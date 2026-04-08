from django.conf import settings
from django.db import models
from django.urls import reverse


def product_image_upload_path(instance, filename):
    return f'products/{filename}'


def resolve_image_reference(value):
    if not value:
        return ''

    image_value = str(value).strip()
    if not image_value:
        return ''

    if image_value.startswith(('http://', 'https://', '/', 'data:')):
        return image_value

    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    return f'{media_url.rstrip("/")}/{image_value.lstrip("/")}'


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=120)
    image = models.URLField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.pk])

    @property
    def primary_image(self):
        image = self.images.filter(is_primary=True).first() or self.images.first()
        if image:
            return image
        return None

    @property
    def primary_image_url(self):
        if self.primary_image:
            return self.primary_image.image_url
        if self.image:
            return resolve_image_reference(self.image)
        return ''

    @property
    def formatted_price(self):
        return f'Rs. {self.price:,.2f}'

    @property
    def cover_image_url(self):
        return resolve_image_reference(self.image)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.URLField(max_length=1000)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f'{self.product.name} image #{self.pk}'

    @property
    def image_url(self):
        return resolve_image_reference(self.image)

    def save(self, *args, **kwargs):
        if not self.pk and not self.product.images.exists():
            self.is_primary = True

        super().save(*args, **kwargs)

        if self.is_primary:
            self.product.images.exclude(pk=self.pk).update(is_primary=False)
        elif not self.product.images.filter(is_primary=True).exists():
            type(self).objects.filter(pk=self.pk).update(is_primary=True)
            self.is_primary = True
