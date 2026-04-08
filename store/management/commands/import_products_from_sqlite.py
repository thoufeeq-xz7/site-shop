import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, transaction
from django.utils import timezone

from store.models import Product, ProductImage


def _parse_datetime(value):
    if not value:
        return timezone.now()
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


class Command(BaseCommand):
    help = 'Import store products and gallery images from a SQLite database into the active database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            default='db.sqlite3',
            help='Path to the source SQLite database file. Defaults to db.sqlite3 in the project root.',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Delete existing Product and ProductImage rows in the active database before importing.',
        )

    def handle(self, *args, **options):
        source_path = Path(options['source'])
        if not source_path.is_absolute():
            source_path = Path(settings.BASE_DIR) / source_path

        if not source_path.exists():
            raise CommandError(f'Source database not found: {source_path}')

        active_db_name = str(connection.settings_dict.get('NAME', ''))
        if active_db_name and Path(active_db_name).resolve() == source_path.resolve():
            raise CommandError('The source SQLite database matches the active database. Choose a different source.')

        source_connection = sqlite3.connect(source_path)
        source_connection.row_factory = sqlite3.Row

        try:
            products = source_connection.execute(
                """
                SELECT id, name, description, price, category, image, created_at
                FROM store_product
                ORDER BY id
                """
            ).fetchall()
            product_images = source_connection.execute(
                """
                SELECT id, product_id, image, is_primary, created_at
                FROM store_productimage
                ORDER BY id
                """
            ).fetchall()
        except sqlite3.Error as exc:
            raise CommandError(f'Unable to read source SQLite database: {exc}') from exc
        finally:
            source_connection.close()

        with transaction.atomic():
            if options['replace']:
                ProductImage.objects.all().delete()
                Product.objects.all().delete()

            imported_products = 0
            imported_images = 0

            for row in products:
                product, created = Product.objects.update_or_create(
                    pk=row['id'],
                    defaults={
                        'name': row['name'],
                        'description': row['description'],
                        'price': row['price'],
                        'category': row['category'],
                        'image': row['image'] or None,
                        'created_at': _parse_datetime(row['created_at']),
                    },
                )
                if created:
                    imported_products += 1

            for row in product_images:
                image, created = ProductImage.objects.update_or_create(
                    pk=row['id'],
                    defaults={
                        'product_id': row['product_id'],
                        'image': row['image'],
                        'is_primary': bool(row['is_primary']),
                        'created_at': _parse_datetime(row['created_at']),
                    },
                )
                if created:
                    imported_images += 1

            sequence_sql = connection.ops.sequence_reset_sql(no_style(), [Product, ProductImage])
            with connection.cursor() as cursor:
                for statement in sequence_sql:
                    cursor.execute(statement)

        self.stdout.write(
            self.style.SUCCESS(
                f'Imported {len(products)} product(s) and {len(product_images)} gallery image(s) from {source_path}.'
            )
        )
        if options['replace']:
            self.stdout.write('Existing catalogue rows were replaced before import.')
        else:
            self.stdout.write(
                f'Created {imported_products} new product row(s) and {imported_images} new image row(s); '
                'existing matching IDs were updated.'
            )
