from pathlib import Path

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Product, ProductImage


def _delete_file_if_unused(image_name):
    if not image_name:
        return

    if Product.objects.filter(image=image_name).exists():
        return

    if ProductImage.objects.filter(image=image_name).exists():
        return

    media_file = Path(ProductImage._meta.get_field('image').storage.path(image_name))
    if media_file.exists():
        media_file.unlink()


def _stash_previous_file(instance, model_class, attribute_name):
    if not instance.pk:
        return

    try:
        previous = model_class.objects.get(pk=instance.pk)
    except model_class.DoesNotExist:
        return

    old_field = getattr(previous, attribute_name)
    new_field = getattr(instance, attribute_name)
    old_name = old_field.name if old_field else ''
    new_name = new_field.name if new_field else ''

    if old_name and old_name != new_name:
        setattr(instance, f'_old_{attribute_name}_name', old_name)


@receiver(pre_save, sender=Product)
def product_pre_save(sender, instance, **kwargs):
    _stash_previous_file(instance, Product, 'image')


@receiver(post_save, sender=Product)
def product_post_save(sender, instance, **kwargs):
    _delete_file_if_unused(getattr(instance, '_old_image_name', ''))


@receiver(post_delete, sender=Product)
def product_post_delete(sender, instance, **kwargs):
    if instance.image:
        _delete_file_if_unused(instance.image.name)


@receiver(pre_save, sender=ProductImage)
def product_image_pre_save(sender, instance, **kwargs):
    _stash_previous_file(instance, ProductImage, 'image')


@receiver(post_save, sender=ProductImage)
def product_image_post_save(sender, instance, **kwargs):
    _delete_file_if_unused(getattr(instance, '_old_image_name', ''))


@receiver(post_delete, sender=ProductImage)
def product_image_post_delete(sender, instance, **kwargs):
    if instance.image:
        _delete_file_if_unused(instance.image.name)
