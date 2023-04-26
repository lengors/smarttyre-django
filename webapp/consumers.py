import json
import cutils

from typing import Any
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .utils import load_crawler


class TyresConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs) -> None:

        # Initialize superclass
        super().__init__(*args, **kwargs)

        # Initialize attributes
        self.__fetcher = None

        # Create crawler list
        self.__crawlers = dict()

    async def connect(self) -> None:

        # Get authenticated user
        user = self.scope.get('user')

        # Verify if user is authenticated
        if user is not None and user.is_authenticated:

            # Create crawlers loader
            get_crawler_credentials = sync_to_async(lambda: list(
                user.usercrawlercredentials_set.all()), thread_sensitive=True)

            # Load crawler credentials
            crawler_credentials = await get_crawler_credentials()

            # Load crawlers into memory
            for crawler_credential in crawler_credentials:

                # Load crawler model
                crawler_model = await sync_to_async(lambda: crawler_credential.crawler, thread_sensitive=True)()

                # Load crawler
                for crawler_type in load_crawler(crawler_model.source_code):

                    # Set credentials
                    crawler = crawler_type(
                        crawler_credential.username, crawler_credential.password)

                    # Try to load cookies
                    try:
                        crawler.loads(
                            crawler_credential.cookies.encode('ansi'))
                    except:
                        pass

                    # Add crawler to list
                    self.__crawlers[crawler_model.name] = crawler

            # Accept connection
            await self.accept()

        # If user is not authenticated, close connection
        else:

            # Reject connection
            await self.close()

    async def disconnect(self, _: Any) -> None:

        # Verify if user is authenticated
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()

        # Check if fetcher is initialized
        if self.__fetcher is not None:

            # Wait for crawlers to stop
            for _ in self.__fetcher:
                pass

            # Reset fetcher
            self.__fetcher = None

        # Create crawlers loader
        get_crawler_credentials = sync_to_async(lambda: list(
            user.usercrawlercredentials_set.all()), thread_sensitive=True)

        # Load crawler credentials
        crawler_credentials = await get_crawler_credentials()

        # Store cookies
        for crawler_credential in crawler_credentials:

            # Load crawler model
            crawler_model = await sync_to_async(lambda: crawler_credential.crawler, thread_sensitive=True)()

            # Get crawler
            crawler = self.__crawlers.get(crawler_model.name)

            # Verify if crawler is initialized
            if crawler is not None:

                # Store cookies
                crawler_credential.cookies = crawler.dumps().decode('ansi')

                # Save changes
                await sync_to_async(lambda: crawler_credential.save(), thread_sensitive=True)()

        # Clear crawlers
        self.__crawlers.clear()

    async def next(self) -> None:

        # Get next products
        try:

            # Get next products
            _, _, next_products = next(self.__fetcher)

            # Send next products
            await self.send(text_data=json.dumps({
                'more': True,
                'tyres': next_products,
            }))

        # If there is no next products, close connection
        except StopIteration:

            # Tell client that there is no more products
            await self.send(text_data=json.dumps({
                'more': False,
                'tyres': list(),
            }))

            # Reset fetcher
            self.__fetcher = None

    async def receive(self, text_data: str) -> None:

        # Verify if user is authenticated
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()

        # Otherwise
        else:

            # Parse JSON data
            query = json.loads(text_data)

            # Get fields
            term = query.get('term')
            quantity = query.get('quantity')

            # Othwerwise, check if requesting next
            if term is None and quantity is None:

                # Verify if fetcher is initialized
                if self.__fetcher is None:

                    # Send error message
                    await self.send(text_data=json.dumps({
                        'errors': ['Fetcher is not initialized.']
                    }))

                # Otherwise, get next products
                else:

                    # Get next products
                    await self.next()

            # Otherwise, validate term and quantity
            elif term is None or not isinstance(quantity, (int, type(None))):

                # Set error messages
                errors = list()

                # Verify if term is valid
                if term is None:
                    errors.append('Invalid term.')

                # Verify if quantity is valid
                if not isinstance(quantity, (int, type(None))):
                    errors.append('Invalid quantity.')

                # Send error message
                await self.send(text_data=json.dumps({
                    'errors': errors
                }))

            # Otherwiae, check if fetcher is initialized
            elif self.__fetcher is not None:
                # Send error message
                await self.send(text_data=json.dumps({
                    'errors': ['Fetcher already initialized.']
                }))

            # Otherwise
            else:

                # Create fetcher
                self.__fetcher = cutils.fetch_all(
                    list(self.__crawlers.values()), (term, quantity))

                # Get next products
                await self.next()
