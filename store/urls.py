from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('health/', views.health_check, name='health_check'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('admin/login/', views.admin_login_view, name='admin_login'),
    path('logout/', views.logout_view, name='logout'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:pk>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order_confirmation/', views.order_confirmation, name='order_confirmation'),
    path('about/', views.about_us, name='about'),
    path('contact/', views.contact_us, name='contact'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/products/', views.admin_product_list, name='admin_product_list'),
    path('admin/products/add/', views.admin_add_product, name='admin_add_product'),
    path('admin/products/<int:pk>/edit/', views.admin_edit_product, name='admin_edit_product'),
    path('admin/products/<int:pk>/delete/', views.admin_delete_product, name='admin_delete_product'),
    path('product-image/<int:pk>/delete/', views.delete_product_image, name='delete_product_image'),
    path('product-image/<int:pk>/set-primary/', views.set_primary_product_image, name='set_primary_product_image'),
]
