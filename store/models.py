from django.db import models
from django.urls import reverse


def product_image_upload_path(instance, filename):
    return f'products/{filename}'


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=120)
    image = models.ImageField(upload_to=product_image_upload_path, blank=True, null=True)
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
            return self.primary_image.image.url
        if self.image:
            return self.image.url
        return ''

    @property
    def formatted_price(self):
        return f'Rs. {self.price:,.2f}'


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=product_image_upload_path)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f'{self.product.name} image #{self.pk}'

    def save(self, *args, **kwargs):
        if not self.pk and not self.product.images.exists():
            self.is_primary = True

        super().save(*args, **kwargs)

        if self.is_primary:
            self.product.images.exclude(pk=self.pk).update(is_primary=False)
        elif not self.product.images.filter(is_primary=True).exists():
            type(self).objects.filter(pk=self.pk).update(is_primary=True)
            self.is_primary = True
