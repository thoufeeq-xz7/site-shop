from decimal import Decimal
from functools import wraps
import logging
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import OperationalError, ProgrammingError
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST, require_safe

from store import admin

from .forms import CheckoutForm, ContactForm, ProductForm, RegistrationForm, StyledAuthenticationForm
from .models import Product, ProductImage

logger = logging.getLogger(__name__)
def ensure_admin_user():
    username = settings.ADMIN_DASHBOARD_USERNAME.strip()
    password = settings.ADMIN_DASHBOARD_PASSWORD


    if not username or not password:
        logger.warning('Admin dashboard credentials are not fully configured.')
        return None

    User = get_user_model()
    user, _created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': settings.ADMIN_DASHBOARD_EMAIL,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
        },
    )

    user_dirty = False
    if user.email != settings.ADMIN_DASHBOARD_EMAIL:
        user.email = settings.ADMIN_DASHBOARD_EMAIL
        user_dirty = True
    if not user.is_staff:
        user.is_staff = True
        user_dirty = True
    if not user.is_active:
        user.is_active = True
        user_dirty = True
    if user.is_superuser:
        user.is_superuser = False
        user_dirty = True
    if not user.check_password(password):
        user.set_password(password)
        user_dirty = True

    if user_dirty:
        user.save()

    return user


def admin_required(view_func):
    @wraps(view_func)
    @login_required(login_url='admin_login')
    def wrapped(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped


def _get_cart(session):
    return session.setdefault('cart', {})


def _set_cart(session, cart):
    session['cart'] = cart
    session.modified = True


def _build_cart_items(request):
    cart = request.session.get('cart', {})
    product_ids = []
    normalized_cart = {}

    for product_id, quantity in cart.items():
        try:
            normalized_product_id = int(product_id)
            normalized_quantity = max(1, int(quantity))
        except (TypeError, ValueError):
            continue
        product_ids.append(normalized_product_id)
        normalized_cart[str(normalized_product_id)] = normalized_quantity

    products = Product.objects.filter(id__in=product_ids).prefetch_related('images')
    product_map = {product.id: product for product in products}
    items = []
    subtotal = Decimal('0.00')

    for product_id, quantity in normalized_cart.items():
        product = product_map.get(int(product_id))
        if not product:
            continue
        line_total = product.price * quantity
        subtotal += line_total
        items.append({'product': product, 'quantity': quantity, 'line_total': line_total})

    return items, subtotal


def _upload_product_images(product, files):
    if not files:
        return

    has_images = product.images.exists()
    uploaded = []

    for index, file in enumerate(files):
        uploaded.append(
            ProductImage.objects.create(
                product=product,
                image=file,
                is_primary=index == 0 and not has_images,
            )
        )

    if uploaded and not product.images.filter(is_primary=True).exists():
        first = uploaded[0]
        first.is_primary = True
        first.save(update_fields=['is_primary'])


def _build_whatsapp_order(items, subtotal, form):
    customer_name = form.cleaned_data['customer_name']
    phone_number = form.cleaned_data['phone_number']
    address = form.cleaned_data['address']
    notes = form.cleaned_data['notes']
    lines = ['Hello StupUp, I would like to place an order:', '']

    for item in items:
        lines.append(f"- {item['product'].name} x {item['quantity']} = Rs. {item['line_total']:.2f}")

    lines.extend(
        [
            '',
            f'Total: Rs. {subtotal:.2f}',
            '',
            f'Name: {customer_name}',
            f'Phone: {phone_number}',
            f'Address: {address}',
        ]
    )

    if notes:
        lines.append(f'Notes: {notes}')

    message = '\n'.join(lines)
    encoded_message = quote(message)
    whatsapp_url = f'https://wa.me/{settings.STORE_WHATSAPP_NUMBER}?text={encoded_message}'

    return {
        'customer_name': customer_name,
        'phone_number': phone_number,
        'address': address,
        'notes': notes,
        'message': message,
        'whatsapp_url': whatsapp_url,
        'total': f'{subtotal:.2f}',
        'item_count': sum(item['quantity'] for item in items),
        'items': [
            {
                'name': item['product'].name,
                'quantity': item['quantity'],
                'price': f'{item["product"].price:.2f}',
                'line_total': f'{item["line_total"]:.2f}',
            }
            for item in items
        ],
    }


@require_safe
def home(request):
    search = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    products = []
    categories = []
    catalog_available = True

    try:
        product_queryset = Product.objects.prefetch_related('images')
        category_queryset = Product.objects.order_by('category').values_list('category', flat=True).distinct()

        if search:
            product_queryset = product_queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if selected_category:
            product_queryset = product_queryset.filter(category__iexact=selected_category)

        products = list(product_queryset)
        categories = list(category_queryset)
    except (OperationalError, ProgrammingError):
        catalog_available = False
        logger.exception('Unable to load catalogue data for the home page.')

    return render(
        request,
        'store/home.html',
        {
            'products': products,
            'categories': categories,
            'selected_category': selected_category,
            'search': search,
            'catalog_available': catalog_available,
        },
    )


@require_safe
def health_check(request):
    return HttpResponse('ok', content_type='text/plain')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Welcome to StupUp. Your account is ready.')
            return redirect('home')
    else:
        form = RegistrationForm()

    return render(request, 'store/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = ''

    form = StyledAuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        messages.success(request, 'You are now signed in.')
        return redirect(next_url or 'home')

    return render(
        request,
        'store/login.html',
        {
            'form': form,
            'next': next_url,
            'show_register_link': True,
        },
    )


def admin_login_view(request):
    try:
        ensure_admin_user()
    except (OperationalError, ProgrammingError):
        logger.exception('Unable to prepare the admin dashboard account.')

    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')

    next_url = request.POST.get('next') or request.GET.get('next') or reverse('admin_dashboard')
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = reverse('admin_dashboard')

    form = StyledAuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if user.is_staff or user.is_superuser:
            login(request, user)
            messages.success(request, 'Welcome back. Admin access is ready.')
            return redirect(next_url or 'admin_dashboard')
        form.add_error(None, 'This account does not have access to the admin dashboard.')

    return render(
        request,
        'store/login.html',
        {
            'form': form,
            'next': next_url,
            'page_title': 'Admin Login | StupUp',
            'eyebrow': 'Admin access',
            'heading': 'Sign in to manage the dashboard.',
            'description': 'Use the admin username and password configured for this store to manage products and catalogue content.',
            'submit_label': 'Open Dashboard',
            'show_register_link': False,
            'alternate_login_url': reverse('login'),
            'alternate_login_label': 'Customer login',
            'next_message': 'You are signing in to continue to the admin dashboard.',
        },
    )


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')


@require_GET
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.prefetch_related('images'), pk=pk)
    return render(request, 'store/product_detail.html', {'product': product})


@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = _get_cart(request.session)
    product_id = str(product.pk)
    cart[product_id] = int(cart.get(product_id, 0)) + 1
    _set_cart(request.session, cart)
    messages.success(request, f'{product.name} added to cart.')
    return redirect(request.POST.get('next') or reverse('checkout'))


@require_POST
def update_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        quantity = max(0, int(request.POST.get('quantity', 1)))
    except (TypeError, ValueError):
        quantity = 1
    cart = _get_cart(request.session)
    product_id = str(product.pk)
    if quantity == 0:
        cart.pop(product_id, None)
    else:
        cart[product_id] = quantity
    _set_cart(request.session, cart)
    messages.success(request, f'Cart updated for {product.name}.')
    return redirect('checkout')


@require_POST
def remove_from_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = _get_cart(request.session)
    cart.pop(str(product.pk), None)
    _set_cart(request.session, cart)
    messages.success(request, f'{product.name} removed from cart.')
    return redirect('checkout')


@login_required
def checkout(request):
    items, subtotal = _build_cart_items(request)
    if not items and not request.session.get('last_order'):
        messages.info(request, 'Your cart is empty. Add a few products to continue.')
        return redirect('home')

    initial = {}
    if request.user.is_authenticated:
        initial['customer_name'] = request.user.get_full_name() or request.user.username

    form = CheckoutForm(request.POST or None, initial=initial)
    order = request.session.get('last_order')

    if request.method == 'POST' and form.is_valid():
        order = _build_whatsapp_order(items, subtotal, form)
        request.session['last_order'] = order
        request.session['cart'] = {}
        request.session.modified = True
        messages.success(request, 'Order summary prepared. You can send it using WhatsApp.')
        items = []
        subtotal = Decimal('0.00')

    return render(
        request,
        'store/checkout.html',
        {'cart_items': items, 'subtotal': subtotal, 'form': form, 'order': order},
    )


@login_required
@require_GET
def order_confirmation(request):
    return redirect('checkout')


@require_GET
def about_us(request):
    return render(request, 'store/about_us.html')


def contact_us(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        messages.success(request, 'Thanks for reaching out. We will get back to you soon.')
        return redirect('contact')
    return render(request, 'store/contact_us.html', {'form': form})


@admin_required
@require_GET
def admin_dashboard(request):
    return render(
        request,
        'store/admin/admin_dashboard.html',
        {
            'product_count': Product.objects.count(),
            'image_count': ProductImage.objects.count(),
            'category_count': Product.objects.values('category').distinct().count(),
            'latest_products': Product.objects.prefetch_related('images')[:5],
        },
    )


@admin_required
@require_GET
def admin_product_list(request):
    search = request.GET.get('q', '').strip()
    products = Product.objects.annotate(image_total=Count('images')).prefetch_related('images')
    if search:
        products = products.filter(Q(name__icontains=search) | Q(category__icontains=search))
    return render(request, 'store/admin/product_list.html', {'products': products, 'search': search})


@admin_required
def admin_add_product(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        _upload_product_images(product, request.FILES.getlist('images'))
        messages.success(request, f'{product.name} created successfully.')
        return redirect('admin_product_list')
    return render(request, 'store/admin/add_product.html', {'form': form})


@admin_required
def admin_edit_product(request, pk):
    product = get_object_or_404(Product.objects.prefetch_related('images'), pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        _upload_product_images(product, request.FILES.getlist('images'))
        messages.success(request, f'{product.name} updated successfully.')
        return redirect('admin_edit_product', pk=product.pk)
    return render(request, 'store/admin/edit_product.html', {'form': form, 'product': product})


@admin_required
@require_POST
def admin_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product_name = product.name
    product.delete()
    messages.success(request, f'{product_name} deleted.')
    return redirect('admin_product_list')


@admin_required
@require_POST
def delete_product_image(request, pk):
    image = get_object_or_404(ProductImage.objects.select_related('product'), pk=pk)
    product = image.product
    deleted_primary = image.is_primary
    image.delete()

    next_image = product.images.first()
    if deleted_primary and next_image:
        next_image.is_primary = True
        next_image.save(update_fields=['is_primary'])

    return JsonResponse({'success': True})


@admin_required
@require_POST
def set_primary_product_image(request, pk):
    image = get_object_or_404(ProductImage.objects.select_related('product'), pk=pk)
    image.product.images.update(is_primary=False)
    image.is_primary = True
    image.save(update_fields=['is_primary'])
    return JsonResponse({'success': True})
