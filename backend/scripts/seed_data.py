#!/usr/bin/env python3
"""Seed script to populate database with sample chat data for testing."""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, init_db
from app.models import Contact, Conversation, Message


# Sample contacts data
SAMPLE_CONTACTS = [
    {
        "phone_number": "+1234567890",
        "name": "John Smith",
        "email": "john.smith@email.com",
        "status": "active",
    },
    {
        "phone_number": "+1987654321",
        "name": "Sarah Johnson",
        "email": "sarah.j@company.com",
        "status": "active",
    },
    {
        "phone_number": "+1555123456",
        "name": "Mike Wilson",
        "email": None,
        "status": "active",
    },
    {
        "phone_number": "+1555987654",
        "name": "Emily Davis",
        "email": "emily.davis@gmail.com",
        "status": "active",
    },
    {
        "phone_number": "+1444555666",
        "name": "Alex Brown",
        "email": None,
        "status": "active",
    },
]

# Sample conversation messages
SAMPLE_CONVERSATIONS = {
    "+1234567890": [
        ("inbound", "Hi! I'm interested in your services", -120),
        ("outbound", "Hello John! Thanks for reaching out. How can I help you today?", -118),
        ("inbound", "I wanted to know more about your pricing plans", -115),
        ("outbound", "Sure! We have three plans: Basic ($29/mo), Pro ($79/mo), and Enterprise (custom). Which features are most important to you?", -110),
        ("inbound", "The Pro plan sounds good. Does it include API access?", -100),
        ("outbound", "Yes, the Pro plan includes full API access with 10,000 requests/month. Would you like me to set up a demo?", -95),
        ("inbound", "That would be great!", -90),
        ("outbound", "Perfect! I'll send you a calendar link shortly. Is there a specific time that works best for you?", -85),
        ("inbound", "Afternoons work best, preferably after 2 PM", -80),
        ("outbound", "Got it! I'll schedule something for tomorrow at 3 PM. You'll receive a confirmation email shortly.", -75),
    ],
    "+1987654321": [
        ("inbound", "Hello, I need help with my account", -60),
        ("outbound", "Hi Sarah! I'd be happy to help. What seems to be the issue?", -58),
        ("inbound", "I can't access my dashboard. It keeps showing an error", -55),
        ("outbound", "I apologize for the inconvenience. Can you tell me what error message you're seeing?", -52),
        ("inbound", "It says 'Session expired. Please login again' but logging in doesn't help", -48),
        ("outbound", "I see. This might be a cache issue. Could you try clearing your browser cache and cookies, then logging in again?", -45),
        ("inbound", "Let me try that...", -42),
        ("inbound", "That worked! Thank you so much! 🙏", -38),
        ("outbound", "Wonderful! Glad I could help. Is there anything else you need assistance with?", -35),
        ("inbound", "No, that's all. Thanks again!", -30),
        ("outbound", "You're welcome! Don't hesitate to reach out if you need anything else. Have a great day! 😊", -28),
    ],
    "+1555123456": [
        ("inbound", "Quick question - do you ship internationally?", -25),
        ("outbound", "Hi Mike! Yes, we ship to over 50 countries. Which country are you in?", -22),
        ("inbound", "Canada", -20),
        ("outbound", "Great news - we ship to Canada! Standard shipping is $15 and takes 5-7 business days. Express is $35 for 2-3 days.", -18),
        ("inbound", "Perfect, thanks!", -15),
    ],
    "+1555987654": [
        ("inbound", "Hi there! Is the summer sale still going on?", -10),
        ("outbound", "Hello Emily! Yes, our summer sale runs until the end of this month. Use code SUMMER30 for 30% off!", -8),
        ("inbound", "Amazing! Does it apply to all products?", -5),
        ("outbound", "It applies to most products except items already on clearance. Is there something specific you're looking at?", -3),
        ("inbound", "I'm eyeing the new collection. Just wanted to make sure!", -2),
        ("outbound", "Yes, the entire new collection is included! Let me know if you need any help choosing. 🛍️", -1),
    ],
    "+1444555666": [
        ("inbound", "Hey, I placed an order yesterday but haven't received a confirmation email", 0),
        ("outbound", "Hi Alex! Let me look into that for you. Could you provide your order number or the email you used?", 2),
    ],
}


async def seed_database():
    """Seed the database with sample data."""
    print("🌱 Starting database seed...")
    
    # Initialize database
    await init_db()
    
    async with async_session_maker() as session:
        session: AsyncSession
        
        # Check if data already exists
        result = await session.execute(select(Contact).limit(1))
        existing = result.scalar_one_or_none()
        
        if existing:
            print("⚠️  Database already has data. Skipping seed.")
            print("   To re-seed, delete the database file and run again.")
            return
        
        now = datetime.now(timezone.utc)
        
        # Create contacts and conversations
        for contact_data in SAMPLE_CONTACTS:
            phone = contact_data["phone_number"]
            
            # Create contact
            contact = Contact(
                phone_number=phone,
                name=contact_data["name"],
                email=contact_data.get("email"),
                status=contact_data["status"],
            )
            session.add(contact)
            await session.flush()  # Get the contact ID
            
            print(f"✅ Created contact: {contact.name} ({phone})")
            
            # Create conversation
            messages_data = SAMPLE_CONVERSATIONS.get(phone, [])
            last_message_time = now + timedelta(minutes=messages_data[-1][2]) if messages_data else now
            
            conversation = Conversation(
                contact_id=contact.id,
                thread_id=f"thread_{phone.replace('+', '')}",
                last_message_at=last_message_time,
                is_active=True,
                unread_count=1 if messages_data and messages_data[-1][0] == "inbound" else 0,
            )
            session.add(conversation)
            await session.flush()  # Get the conversation ID
            
            print(f"   📝 Created conversation ID: {conversation.id}")
            
            # Create messages
            for sender_type, content, minutes_ago in messages_data:
                message_time = now + timedelta(minutes=minutes_ago)
                
                message = Message(
                    conversation_id=conversation.id,
                    whatsapp_message_id=f"wamid_{conversation.id}_{abs(minutes_ago)}_{sender_type[:2]}",
                    sender_type=sender_type,
                    message_type="text",
                    content=content,
                    status="read" if sender_type == "inbound" else "delivered",
                    created_at=message_time,
                )
                session.add(message)
            
            print(f"   💬 Created {len(messages_data)} messages")
        
        await session.commit()
        print("\n✨ Database seeded successfully!")
        print(f"   Created {len(SAMPLE_CONTACTS)} contacts with conversations and messages.")


if __name__ == "__main__":
    asyncio.run(seed_database())

