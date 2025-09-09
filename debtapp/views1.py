from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import Sum
from decimal import Decimal
from datetime import timedelta

from .forms import UserRegisterForm, TransactionSearchForm, DebtorForm, TransactionForm
from .models import Debtor, Transaction, CustomUser


# Profile View
@login_required
def creditor_detail(request):
    creditor = request.user
    return render(request, 'creditor_detail.html', {'creditor': creditor})


# Register View
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})


# Login View
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


# Dashboard View
@login_required
def dashboard(request):
    qs = Debtor.objects.filter(created_by=request.user)

    total_debtors = qs.count()
    active_debtors = qs.filter(debtor_status='active', is_delete=False).count()
    recovered_debtors = qs.filter(debtor_status='recovered').count()
    deleted_debtors = qs.filter(is_delete=True).count()

    totals = Transaction.objects.filter(debtor__created_by=request.user).aggregate(
        total_debit_amount=Sum('debit_amount') or 0,
        total_credit_amount=Sum('credit_amount') or 0
    )

    total_debit_amount = totals['total_debit_amount'] or 0
    total_credit_amount = totals['total_credit_amount'] or 0
    total_current_debt = total_debit_amount - total_credit_amount

    context = {
        'total_debtors': total_debtors,
        'active_debtors': active_debtors,
        'recovered_debtors': recovered_debtors,
        'deleted_debtors': deleted_debtors,
        'total_debt_amount': total_debit_amount,
        'total_current_debt': total_current_debt,
        'total_recovered_debt': total_credit_amount
    }
    return render(request, 'dashboard.html', context)


# Logout View
def log_out(request):
    logout(request)
    return redirect('login_view')


# Add Debtor
@login_required
def add_debtor(request):
    debtor_limit = 50
    debtor_count = Debtor.objects.filter(is_delete=False, created_by=request.user).count()
    if debtor_count >= debtor_limit:
        return render(request, 'limit_exceeded.html')

    if request.method == 'POST':
        form = DebtorForm(request.POST, request.FILES)
        if form.is_valid():
            debtor = form.save(commit=False)
            debtor.created_by = request.user
            debtor.save()

            Transaction.objects.create(
                debtor=debtor,
                tran_type='debit',
                tran_amount=debtor.initial_debt,
                debit_amount=debtor.initial_debt,
                credit_amount=0,
                current_debt=debtor.initial_debt
            )

            messages.success(request, "1 debtor has been successfully created.")
            return redirect('debtor_list')
    else:
        form = DebtorForm()
    return render(request, 'add_debtor.html', {'form': form})


# Debtor List
@login_required
def debtor_list(request):
    debtors = Debtor.objects.filter(created_by=request.user, is_delete=False)
    return render(request, 'debtor_list.html', {'debtors': debtors})


# Edit Debtor
@login_required
def debtor_edit(request, debtor_id):
    debtor = get_object_or_404(Debtor, id=debtor_id, created_by=request.user, is_delete=False)

    if request.method == 'POST':
        form = DebtorForm(request.POST, instance=debtor)
        if form.is_valid():
            debtor_obj = form.save(commit=False)
            debtor_obj.initial_debt = debtor.initial_debt
            debtor_obj.save()
            messages.success(request, '1 debtor has been successfully updated.')
            return redirect('debtor_list')
    else:
        form = DebtorForm(instance=debtor)
    return render(request, 'debtor_edit.html', {'form': form, 'debtor': debtor})


# Transaction Search
@login_required
def transaction_search(request):
    debtor_qs = Debtor.objects.filter(is_delete=False, created_by=request.user)

    if request.method == 'POST':
        form = TransactionSearchForm(request.POST)
        if form.is_valid():
            debtor_id = form.cleaned_data['debtor_id']
            tran_type = form.cleaned_data['tran_type']
            return redirect(f"{reverse('add_transaction')}?debtor_id={debtor_id}&tran_type={tran_type}")
    else:
        form = TransactionSearchForm()

    return render(request, 'transaction_search.html', {'form': form, 'debtor': debtor_qs})


# Add Transaction
@login_required
@db_transaction.atomic
def add_transaction(request):
    debtor_id = request.GET.get('debtor_id')
    tran_type = request.GET.get('tran_type')

    if not debtor_id or not tran_type:
        # messages.error(request, "Missing debtor information.")
        return redirect('transaction_search')
    
     # Lock the debtor row for this transaction
    debtor = get_object_or_404(
        Debtor.objects.select_for_update(),
        debtor_id=debtor_id,
        created_by=request.user,
        is_delete=False,
    )

    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES)
        if form.is_valid():
            tran_amount = Decimal(form.cleaned_data['tran_amount'])
            tran_medium = form.cleaned_data['tran_medium']
            tran_desc = form.cleaned_data.get('tran_desc', '').strip()
            tran_voucher = form.cleaned_data.get('tran_voucher')

            # Validation for positive transaction amount
            if tran_amount <= 0:
                messages.error(request, "Transaction amount must be positive.")
                # re-render preserving query params
                return render(request,'add_transaction', {'form':form, 'debtor_id':debtor_id,
                                                          'tran_type':tran_type})
            current_before = debtor.current_debt
        
            # Compute new balance based on transaction type
            if tran_type == 'debit':
                current_after = debtor.before + tran_amount
                debit_amount = tran_amount
                credit_amount = Decimal(0)
                debtor.debtor_status = 'active'
            else:  # credit
                if tran_amount > current_before:
                    messages.error(request, "Cannot enter amount greater than current debt.")
                    return render(request, 'add_transaction.html', {
                        'form': form, 'debtor_id': debtor_id, 'tran_type': tran_type,
                    })
                current_after = current_before - tran_amount
                credit_amount = tran_amount
                debit_amount = Decimal(0)
                if current_after == 0:
                    # is_debt_settle = True  # Debt is settled when current debt is zero
                    debtor.debtor_status = 'recovered'
            # Create the transaction record
            Transaction.objects.create(
                debtor=debtor,
                recorded_by=request.user,
                debit_amount=debit_amount,
                credit_amount=credit_amount,
                tran_amount=tran_amount,
                tran_type=tran_type,
                tran_medium=tran_medium,
                tran_desc=tran_desc,
                current_debt=current_after,
                tran_voucher=tran_voucher,
                # is_debt_settle=is_debt_settle,  # Debt settlement flag
            )
            debtor.save(update_fields = ['debtor_status'])
            messages.success(request, f"{tran_type.title()} transaction added successfully.")
            return redirect('debtor_list')
    else:
        form = TransactionForm()

    return render(request, 'add_transaction.html', {
        'form': form,
        'debtor_id': debtor_id,
        'tran_type': tran_type,
    })


# Debtor Detail
@login_required
def debtor_detail(request, debtor_id):
    debtor = get_object_or_404(Debtor, id=debtor_id, created_by=request.user)
    transactions = Transaction.objects.filter(debtor=debtor)
    return render(request, 'debtor_detail.html', {'debtor': debtor, 'transactions': transactions})


# Voucher View
@login_required
def voucher_view(request, pk):
    debtor = Debtor.objects.filter(id=pk, created_by=request.user).first()
    if debtor:
        return render(request, 'voucher_view.html', {'debtor': debtor})

    transaction = get_object_or_404(Transaction, id=pk, debtor__created_by=request.user)
    return render(request, 'voucher_view.html', {'transaction': transaction})


# Soft Delete Debtor
@login_required
def delete_debtor(request, id):
    debtor = get_object_or_404(Debtor, id=id)
    transactions = Transaction.objects.filter(debtor=debtor)
    
    if debtor.debtor_status == 'recovered':
        debtor.is_delete = True
        debtor.delete_date = timezone.now()
        debtor.save()
        messages.success(request, "1 Debtor has been successfully deleted.")
    else:
        messages.error(request, "Debt is still pending. Cannot delete debtor.")

    return redirect('debtor_list')


# Recycle Bin for Debtors
@login_required
def recycle_debtor(request):
    debtors = Debtor.objects.filter(created_by=request.user, is_delete=True)
    threshold = timezone.now() - timedelta(days=20)
    expired_debtors = Debtor.objects.filter(is_delete=True, delete_date__lt=threshold, created_by=request.user)

    if expired_debtors.exists():
        expired_debtors.delete()

    return render(request, 'recycle_debtor.html', {'debtors': debtors})


# Restore Debtor
@login_required
def restore_debtor(request, id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('debtor_list')

    debtor = get_object_or_404(Debtor, id=id, created_by=request.user)
    debtor.is_delete = False
    debtor.save()
    messages.success(request, "Debtor restored successfully.")
    return redirect('debtor_list')


# Hard Delete Debtor
@login_required
def hard_delete_debtor(request, id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('debtor_list')

    debtor = get_object_or_404(Debtor, id=id, created_by=request.user)
    if debtor.debtor_status == 'recovered':
        debtor.delete()
        messages.success(request, "Debtor permanently deleted.")
    else:
        messages.error(request, "Cannot delete debtor with pending debt.")
    return redirect('debtor_list')
