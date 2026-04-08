import shutil
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from store.models import Product, ProductImage


class StoreRouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            name='Route Test Product',
            description='Smoke test product',
            price='99.99',
            category='Testing',
        )
        cls.user = get_user_model().objects.create_user(
            username='route-user',
            password='RouteUser123!',
        )

    def test_home_route_uses_root_path(self):
        self.assertEqual(reverse('home'), '/')

    def test_public_pages_load(self):
        for route_name in ['home', 'register', 'login', 'admin_login', 'about', 'contact']:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_admin_login_hides_customer_signup_prompt(self):
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Create an account')

    def test_health_check_returns_ok(self):
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    def test_product_detail_page_loads(self):
        response = self.client.get(reverse('product_detail', args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)

    def test_product_detail_uses_database_image_url(self):
        ProductImage.objects.create(
            product=self.product,
            image='https://cdn.example.com/products/route-test-primary.jpg',
            is_primary=True,
        )

        response = self.client.get(reverse('product_detail', args=[self.product.pk]))

        self.assertContains(response, 'https://cdn.example.com/products/route-test-primary.jpg')

    def test_login_accepts_valid_credentials(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'route-user', 'password': 'RouteUser123!'},
        )
        self.assertRedirects(response, reverse('home'))

    def test_protected_routes_redirect_when_logged_out(self):
        for route_name in ['checkout', 'admin_dashboard', 'admin_product_list', 'admin_add_product']:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 302)

    @override_settings(
        ADMIN_DASHBOARD_USERNAME='storeadmin',
        ADMIN_DASHBOARD_PASSWORD='ChangeMe123!',
        ADMIN_DASHBOARD_EMAIL='storeadmin@example.com',
    )
    def test_admin_login_creates_configured_admin_user(self):
        response = self.client.post(
            reverse('admin_login'),
            {'username': 'storeadmin', 'password': 'ChangeMe123!'},
        )

        self.assertRedirects(response, reverse('admin_dashboard'))

        admin_user = get_user_model().objects.get(username='storeadmin')
        self.assertTrue(admin_user.is_staff)
        self.assertFalse(admin_user.is_superuser)

    @patch('store.views.Product.objects.prefetch_related', side_effect=OperationalError('db down'))
    def test_home_page_still_renders_when_catalog_is_unavailable(self, _mock_prefetch_related):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'catalogue is temporarily unavailable')

    def test_admin_add_product_saves_up_to_three_gallery_urls_in_database(self):
        admin_user = get_user_model().objects.create_user(
            username='catalog-admin',
            password='CatalogAdmin123!',
            is_staff=True,
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse('admin_add_product'),
            {
                'name': 'URL Product',
                'description': 'Stored entirely in the database.',
                'price': '249.99',
                'category': 'Database',
                'image': 'https://cdn.example.com/products/url-product-cover.jpg',
                'gallery_image_1': 'https://cdn.example.com/products/url-product-1.jpg',
                'gallery_image_2': 'https://cdn.example.com/products/url-product-2.jpg',
                'gallery_image_3': 'https://cdn.example.com/products/url-product-3.jpg',
            },
        )

        self.assertRedirects(response, reverse('admin_product_list'))
        product = Product.objects.get(name='URL Product')
        self.assertEqual(product.image, 'https://cdn.example.com/products/url-product-cover.jpg')
        self.assertEqual(product.images.count(), 3)
        self.assertEqual(
            list(product.images.values_list('image', flat=True)),
            [
                'https://cdn.example.com/products/url-product-1.jpg',
                'https://cdn.example.com/products/url-product-2.jpg',
                'https://cdn.example.com/products/url-product-3.jpg',
            ],
        )

    def test_admin_add_product_uploads_files_and_stores_generated_urls_in_database(self):
        admin_user = get_user_model().objects.create_user(
            username='upload-admin',
            password='UploadAdmin123!',
            is_staff=True,
        )
        self.client.force_login(admin_user)

        media_root = settings.BASE_DIR / 'test-media'
        shutil.rmtree(media_root, ignore_errors=True)

        try:
            with override_settings(MEDIA_ROOT=media_root, MEDIA_URL='/media/'):
                cover_file = SimpleUploadedFile('cover.jpg', b'cover-image-bytes', content_type='image/jpeg')
                gallery_file_1 = SimpleUploadedFile('gallery-1.jpg', b'gallery-image-1', content_type='image/jpeg')
                gallery_file_2 = SimpleUploadedFile('gallery-2.jpg', b'gallery-image-2', content_type='image/jpeg')

                response = self.client.post(
                    reverse('admin_add_product'),
                    {
                        'name': 'Uploaded Product',
                        'description': 'Admin uploaded files and the app generated URLs.',
                        'price': '399.99',
                        'category': 'Uploads',
                        'cover_image_file': cover_file,
                        'gallery_image_files': [gallery_file_1, gallery_file_2],
                    },
                )
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

        self.assertRedirects(response, reverse('admin_product_list'))
        product = Product.objects.get(name='Uploaded Product')
        self.assertTrue(product.image.startswith('http://testserver/media/products/'))
        self.assertEqual(product.images.count(), 2)
        self.assertTrue(
            all(image.startswith('http://testserver/media/products/') for image in product.images.values_list('image', flat=True))
        )
