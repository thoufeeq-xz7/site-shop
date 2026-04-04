from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from store.models import Product, ProductImage


class Command(BaseCommand):
    help = 'List or delete unused files in media/products.'

    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true', help='Delete unused files instead of listing them.')

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT) / 'products'
        media_root.mkdir(parents=True, exist_ok=True)

        referenced = {
            image_name
            for image_name in Product.objects.exclude(image='').values_list('image', flat=True)
            if image_name
        }
        referenced.update(
            {
                image_name
                for image_name in ProductImage.objects.exclude(image='').values_list('image', flat=True)
                if image_name
            }
        )

        candidates = [path for path in media_root.rglob('*') if path.is_file() and not path.name.startswith('.')]
        unused = [path for path in candidates if path.relative_to(settings.MEDIA_ROOT).as_posix() not in referenced]

        if not unused:
            self.stdout.write(self.style.SUCCESS('No unused images found.'))
            return

        for path in unused:
            relative = path.relative_to(settings.MEDIA_ROOT).as_posix()
            if options['delete']:
                path.unlink()
                self.stdout.write(self.style.WARNING(f'Deleted {relative}'))
            else:
                self.stdout.write(relative)

        if not options['delete']:
            self.stdout.write(self.style.SUCCESS(f'Found {len(unused)} unused image(s).'))
