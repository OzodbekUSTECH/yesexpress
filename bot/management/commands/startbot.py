import asyncio

from django.core.management.base import BaseCommand

from bot.bot import main


class Command(BaseCommand):
    help = "Starts bot"

    def handle(self, *args, **options):
        asyncio.run(main())
