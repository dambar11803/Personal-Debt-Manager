from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Debtor, Transaction
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone 
from django.contrib.auth.forms import AuthenticationForm

phone_regex = RegexValidator(
    regex=r'^\d{10}$',
    message="Phone number must be 10 digits long numbers."
)

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    mobile = forms.CharField(
        max_length=10,
        validators=[phone_regex],
        help_text="10 digit mobile number"
    )
    address = forms.CharField(max_length=200)
    profile_pic = forms.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'mobile', 'address', 'profile_pic',
            'password1', 'password2'
        ]

class DebtorForm(forms.ModelForm):
    class Meta:
        model = Debtor
        fields = ['name', 'address', 'mobile', 'initial_debt','debt_date','debt_purpose', 'payment_method','voucher_cheque_no','debt_voucher']
        # exclude = [
        #     'created_by', 'total_debt', 'is_deleted', 
        #     'deleted_at', 'deleted_by', 'status','is_delete','delete_date','debtor_id','debtor_status'
        # ]
        widgets = {
            'debt_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
        }
        

    def clean_debt_date(self):
        debt_date = self.cleaned_data.get('debt_date')
        if debt_date and debt_date > timezone.now().date():
            raise ValidationError("Debt date cannot be in the future")
        return debt_date
    
    def __init__(self,*args,**kwargs):
        super().__init__(*args, **kwargs) 
        
        #only check if editing an existing debtor 
        if self.instance and self.instance.pk:
            #check if any transaction exists for this debtor 
            if self.instance.transactions.count()>1:
                self.fields['initial_debt'].disabled = True 
        
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        exclude = ['recorded_by', 'debtor', 'current_debt','debit_amount','credit_amount','tran_type','tran_id']

#Transacton Search Form 
class TransactionSearchForm(forms.Form):
    debtor_id = forms.CharField(max_length=7, label="Debtor ID")
    TRAN_TYPE_CHOICES = [
        ('debit', 'debit'),
        ('credit', 'credit'),
    ]
    tran_type = forms.ChoiceField(choices=TRAN_TYPE_CHOICES, label="Transaction Type")

  