from django.test import TestCase
from django.urls import reverse

from store.models import Product


class StoreRouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            name='Route Test Product',
            description='Smoke test product',
            price='99.99',
            category='Testing',
        )

    def test_home_route_uses_root_path(self):
        self.assertEqual(reverse('home'), '/')

    def test_public_pages_load(self):
        for route_name in ['home', 'register', 'login', 'about', 'contact']:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_health_check_returns_ok(self):
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    def test_product_detail_page_loads(self):
        response = self.client.get(reverse('product_detail', args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)

    def test_protected_routes_redirect_when_logged_out(self):
        for route_name in ['checkout', 'admin_dashboard', 'admin_product_list', 'admin_add_product']:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 302)
