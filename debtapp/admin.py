from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Debtor, Transaction 

class CustomUserAdmin(UserAdmin):
    # Add new fields to the admin form
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('mobile', 'address', 'profile_pic')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('mobile', 'address', 'profile_pic')}),
    )

# Debtor admin
class DebtorAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile', 'total_debt', 'payment_method', 'created_by', 'debt_date')
    list_filter = ('payment_method', 'debt_date')
    search_fields = ('name', 'mobile', 'purpose')
    readonly_fields = ('debt_date',)

# Transaction admin
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('debtor', 'tran_type', 'tran_amount', 'tran_medium', 'recorded_by', 'tran_date', 'current_debt')
    list_filter = ('tran_type', 'tran_medium', 'tran_date')
    search_fields = ('debtor__name', 'tran_desc')
    readonly_fields = ('tran_date',)

# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Debtor, DebtorAdmin)
admin.site.register(Transaction, TransactionAdmin)


