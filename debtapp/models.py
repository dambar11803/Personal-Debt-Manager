from django.contrib.auth.models import AbstractUser
from django.db import models 
from django.conf import settings 
from django.db import transaction 
from django.core.exceptions import ValidationError 
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator 
import os
import uuid
from django.utils import timezone
from magic import Magic

# ========================
# Utility Functions
# ========================
def user_profile_pic(instance, filename):
    #generate unique path for user profile pictures
    ext = os.path.splitext(filename)[1].lower()
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{instance.username}_{unique_id}{ext}"
    return os.path.join('profile_pics', instance.username,filename)

# def user_profile_pic(instance, filename):
#     """Generate path for user profile pictures"""
#     ext = os.path.splitext(filename)[1].lower()
#     filename = f"{instance.username}{ext}"
#     return os.path.join('profile_pics/', instance.username, filename)

def validate_file_extension(value):
    """Validate file extensions"""
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.pdf']
    if ext not in valid_extensions:
        raise ValidationError(f'Unsupported file extension. Allowed: {", ".join(valid_extensions)}')

def validate_file_size(value):
    """Validate file size (max 1MB)"""
    max_size = 1 * 1024 * 1024  # 1MB
    if value.size > max_size:
        raise ValidationError("File size must be under 1MB.")

def validate_file_content(value):
    """Validate file content using magic"""
    mime = Magic(mime=True)
    file_mime_type = mime.from_buffer(value.read(1024))
    value.seek(0)
    
    if not any(file_mime_type.startswith(mime_type) 
       for mime_type in ['image/', 'application/pdf']):
        raise ValidationError("Only images and PDFs are allowed.")

phone_regex = RegexValidator(
    regex=r'^\d{10}$',
    message="Phone number must be 10 digits long numbers."
)

# ========================
# Models
# ========================
class CustomUser(AbstractUser):
    """Extended User model with additional fields"""
    mobile = models.CharField(
        max_length=14, 
        unique=True, 
        null= True,
        blank=True,
        default=None,
        validators=[phone_regex]
    )
    address = models.TextField(max_length=200)
    profile_pic = models.ImageField(
        upload_to=user_profile_pic,
        validators=[validate_file_extension, validate_file_size, validate_file_content],
        blank=True,
        null=True
    )
    
    user_created_at = models.DateField(auto_now_add=True, blank=True, null=True)
    def __str__(self):
        return f"{self.username}"

PAYMENT_MEDIUM = [
    ('cash', 'Cash'),
    ('mobile_banking', 'Mobile Banking'),
    ('esewa', 'eSewa'),
    ('khalti', 'Khalti'),
    ('ime', 'IME'),
    ('connectips', 'ConnectIPS'),
    ('fonepay', 'FonePay'),
]

class Debtor(models.Model):
    """Model representing debtors"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('recovered', 'Recovered'),

    ]
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='debtors'
    )
    debtor_id = models.CharField(max_length=10, unique=True, editable=False)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    mobile = models.CharField(max_length=10, validators=[phone_regex],unique=True)
    total_debt = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.0,
        validators=[MinValueValidator(0.0)]
    )
    initial_debt = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.0
    )
    debt_date = models.DateField()
    debt_purpose = models.CharField(max_length=100)
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_MEDIUM, 
        default='cash'
    )
    voucher_cheque_no = models.CharField(max_length=30, blank=True)
    debt_voucher = models.FileField(
        upload_to='debt_vouchers/',
        validators=[validate_file_extension, validate_file_size, validate_file_content],
        blank=True,
        null=True
    )
    is_delete = models.BooleanField(default=False)
    delete_date = models.DateTimeField(null=True, blank=True)
    debtor_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    # New fields to distinguish between admin and user
    is_admin = models.BooleanField(default=False)  # If true, user is admin
    is_user = models.BooleanField(default=True)   # If true, user is a regular user  
    
    def save(self, *args, **kwargs):
        """Custom save to enforce business logic"""
        if self.is_admin and self.is_user:
            raise ValidationError("A user cannot be both admin and regular user.")
        
        # Automatically set the user type based on the admin flag
        if self.is_admin:
            self.is_user = False  # If user is admin, they can't be a regular user
        elif self.is_user:
            self.is_admin = False  # If user is regular user, they can't be admin
            
        super().save(*args, **kwargs)

    # class Meta:
    #     ordering = ['-created_at']
    #     verbose_name = 'Debtor'
    #     verbose_name_plural = 'Debtors'

    def clean(self):
        """Additional validation"""
        if self.initial_debt < 0:
            raise ValidationError({'initial_debt': 'Debt amount cannot be negative'})
        
        if self.total_debt < 0:
            raise ValidationError({'total_debt': 'Total debt cannot be negative'})

    def save(self, *args, **kwargs):
        """Custom save to generate debtor_id"""
        if not self.debtor_id:
            with transaction.atomic():
                super().save(*args, **kwargs)  # First save to get PK
                self.debtor_id = f"D{self.pk:05d}"
                kwargs['force_insert'] = False
                super().save(update_fields=['debtor_id'], *args, **kwargs)
        else:
            super().save(*args, **kwargs)

 
    @property
    def current_debt(self):
        """Calculate current debt from transactions"""
        latest_tran = self.transactions.order_by('-tran_date').first()
        return latest_tran.current_debt if latest_tran else self.total_debt

   
    def __str__(self):
        return f"{self.name} ({self.debtor_id})"

class Transaction(models.Model):
    """Model representing debt transactions"""
    TRANSACTION_TYPES = [
        ('debit', 'debit'),
        ('credit', 'credit'),

    ]
    
    debtor = models.ForeignKey(
        Debtor, 
        related_name='transactions', 
        on_delete=models.CASCADE
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transactions'
    )
    tran_id = models.CharField(max_length=10, unique=True, editable=False)
    tran_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    debit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tran_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_debt = models.DecimalField(max_digits=12, decimal_places=2)
    tran_desc = models.CharField(max_length=200)
    tran_medium = models.CharField(
        max_length=20, 
        choices=PAYMENT_MEDIUM, 
        default='cash'
    )
    tran_voucher = models.FileField(
        upload_to='tran_vouchers/',
        validators=[validate_file_extension, validate_file_size, validate_file_content],
        blank=True,
        null=True
    )
    tran_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # class Meta:
    #     ordering = ['-tran_date']
    #     verbose_name = 'Transaction'
    #     verbose_name_plural = 'Transactions'

    def clean(self):
        """Validate transaction amounts"""
        if self.tran_amount <= 0:
            raise ValidationError({'tran_amount': 'Amount must be positive'})

    def save(self, *args, **kwargs):
        """Generate transaction ID and calculate current debt"""
        if not self.tran_id:
            last_tran = Transaction.objects.order_by('-id').first()
            last_num = int(last_tran.tran_id[4:]) if last_tran else 0
            self.tran_id = f"Txn{last_num + 1:05d}"
        
              
        super().save(*args, **kwargs)
        
        # Update debtor status if debt is fully recovered
        if self.current_debt <= 0:
            self.debtor.debtor_status = 'recovered'
            self.debtor.save(update_fields=['debtor_status'])

    @property
    def is_voucher_pdf(self):
        """Check if voucher is PDF"""
        return (self.tran_voucher and 
                self.tran_voucher.name.lower().endswith('.pdf'))

    def __str__(self):
        return (f"{self.tran_id} - {self.debtor.name} - "
                f"{self.tran_type} ${self.tran_amount}")