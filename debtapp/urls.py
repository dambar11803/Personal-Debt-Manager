from django.urls import path
from django.contrib.auth import views as auth_views
from . import views  # your custom views 
from . views import * 
from django.contrib.auth import views as auth_views 
from django.urls import reverse_lazy

urlpatterns = [
    # Register
    path('register/', views.register, name='register'),

    # Login - using custom view OR Django's built-in
    path('', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),

    # Logout
#     path('logout/', auth_views.LogoutView.as_view(
#         template_name='registration/logout.html'
#     ), name='logout'),
    
    path('dashboard/', views.dashboard, name='user_dashboard'),
    path('redirect/', custom_redirect_view, name='custom_redirect'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('logout/', views.log_out, name = 'logout'),
    path('creditor-detail/', views.creditor_detail, name='user_profile'),  
    path('debtors-list/', views.debtor_list, name='debtor_list'),
    path('debtors/add/', views.add_debtor, name='add_debtor'),
    path('debtors-detail/<int:debtor_id>/', views.debtor_detail, name='debtor_detail'),
    path('debtors-edit/<int:debtor_id>/edit/', views.debtor_edit, name='debtor_edit'),
    # path('debtors/<int:debtor_id>/transaction/', views.add_transaction, name='add_transaction'),  
    path('transaction-search/',views.transaction_search, name='transaction_search'),
    path('transaction/add/', views.add_transaction, name='add_transaction'),
    path('voucher/<int:pk>/', views.voucher_view, name='voucher_view'),
    path('delete-debtor/<int:id>/', views.delete_debtor, name="delete_debtor"),
    path('recycle-debtor/',views.recycle_debtor, name='recycle_debtor'),
    path('debtor/restore/<int:id>/', views.restore_debtor, name='restore_debtor'),
    path('hard-delete/delete/<int:id>/', views.hard_delete_debtor, name='hard_delete_debtor'),
    path('reports/', views.reports, name='reports'),
    path("reports/summary-details/", views.summary_details, name="summary_details"),
    path("reports/export-debtors/", views.all_debtors_xls, name="all_debtors_xls"),
    path("reports/debtors-transactions/", views.debtor_transactions_xls, name="debtor_transactions_xls"),
    
    # Password change URLs
    path('password_change/', 
         auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html'), 
         name='password_change'),
    path('password_change/done/', 
         auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), 
         name='password_change_done'),
     
     # Password reset
    path('password_reset/',
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'),
         name='password_reset'),

    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),
         name='password_reset_confirm'),

    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),
    
    # Admin URLs
    path('admin-creditor-detail/<int:pk>/', admin_creditor_detail, name="admin_creditor_detail"),
    path('admin-debtor-detail/<int:pk>/', admin_debtor_detail, name="admin_debtor_detail"),
    path('admin-profile/', admin_profile, name= 'admin_profile'),
    path('admin-reports/', views.admin_reports, name='admin_reports'),
    
    # Password-Change for Admin 
    path('admin_password_change/', 
         auth_views.PasswordChangeView.as_view(template_name='admin1180/admin_password_change_form.html',
         success_url=reverse_lazy('admin_password_change_done')), name='admin_password_change'),
    
    path('admin_password_change/done/', 
         auth_views.PasswordChangeDoneView.as_view(template_name='admin1180/admin_password_change_done.html'), 
         name='admin_password_change_done'),
    
    # Export URLs
    path('export/users/', views.export_all_users_xlsx, name='export_all_users_xlsx'),
    path('export/debtors/', views.export_all_debtors_xlsx, name='export_all_debtors_xlsx'),
    path('export/transactions/', views.export_all_transactions_xlsx, name='export_all_transactions_xlsx'),
    path('export/debtor-transactions/', views.export_debtor_transactions_xlsx, name='export_debtor_transactions_xlsx'),
    path('terms-condition/', views.terms_condition, name='terms_condition'),
    path('user-manual/', views.user_manual, name='user_manual'),
]