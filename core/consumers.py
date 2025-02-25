# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class AuctionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.auction_id = self.scope['url_route']['kwargs']['auction_id']
        self.group_name = f"auction_{self.auction_id}"

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def new_bid(self, event):
        """
        Broadcast new bid info to every subscriber
        """
        bid_amount = event['bid_amount']
        user_email = event['user_email']

        await self.send(text_data=json.dumps({
            'type': 'new_bid',
            'bid_amount': bid_amount,
            'user_email': user_email,
        }))
