import asyncio
import json
import base64
import logging
import websockets
import traceback
from websockets.exceptions import ConnectionClosed
# from multi_agent_orchestrator.prompt import ORCHESTRATOR_PROMPT as SYSTEM_INSTRUCTION
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Constants
PROJECT_ID = "sanskaraAI"
LOCATION = "us-central1"
MODEL = "gemini-2.0-flash-exp"
VOICE_NAME = "Puck"

# Audio sample rates for input/output
RECEIVE_SAMPLE_RATE = 24000  # Rate of audio received from Gemini
SEND_SAMPLE_RATE = 16000     # Rate of audio sent to Gemini

# Mock function for get_order_status - shared across implementations
def get_order_status(order_id):
    pass

SYSTEM_INSTRUCTION = """
Here's an updated and expanded checklist, integrating your valuable suggestions, with a stronger emphasis on photography, vendor management, and specific timeline considerations.

Phase 1: Initial Planning & Foundation (12+ Months Before)
Budget & Financials
[ ] Determine overall wedding budget with both families.
[ ] Discuss contributions from each side.
[ ] Create a detailed budget breakdown for each category (venue, catering, attire, decor, photography, entertainment, gifts, etc.).
[ ] Set aside a contingency fund (10-15% of total budget) for unexpected costs or backup vendor needs.
[ ] Explore payment schedules for major vendors.
[ ] Consider wedding insurance.
[ ] Set up a dedicated bank account for wedding expenses.
Vision & Guest List
[ ] Discuss and finalize the overall wedding vision, theme, and style (traditional, modern, fusion, specific regional).
[ ] Create a preliminary guest list for each family (initial count for venue capacity).
[ ] Discuss and decide on the number of events (e.g., Roka, Mehendi, Sangeet, Haldi, Wedding Ceremony, Reception).
[ ] Decide on key decision-makers and communication channels between families.
Key Bookings & Consultations
[ ] Consult an astrologer for auspicious wedding dates (Muhurtham).
[ ] Hire a Wedding Planner (Optional but highly recommended for large Indian weddings): If using one, finalize contract and scope of services.
[ ] Book Wedding Venue(s):
[ ] Ceremony venue (Mandap area).
[ ] Reception venue.
[ ] Pre-wedding event venues (Mehendi, Sangeet, Haldi).
[ ] Check capacity, facilities (AC, parking, restrooms), in-house services, cancellation policy.
[ ] Crucial: Conduct detailed venue visits and finalize contracts, discussing layout, power points, vendor access, and specific entry/exit protocols.
[ ] Book Priest/Pandit: Discuss rituals, duration, specific requirements, and any items they need for the ceremonies.
[ ] Research & Book Photographer & Videographer: Review portfolios, discuss style (candid, traditional), deliverables (albums, videos), and packages. Crucial: Discuss and include pre-wedding and post-wedding photoshoot plans in the package/contract.
[ ] Start Moodboard Collections: Begin gathering inspiration for decor, photography styles, attire, themes, etc., using platforms like Pinterest.
Phase 2: Design & Details (9-11 Months Before)
Attire & Styling
[ ] Bride's Attire:
[ ] Wedding Lehenga/Saree (for main ceremony).
[ ] Reception Gown/Saree.
[ ] Outfits for pre-wedding events (Mehendi, Sangeet, Haldi, Puja).
[ ] Accessories: Footwear, hair accessories, bridal clutch/potli.
[ ] Trousseau shopping (for post-wedding).
[ ] Groom's Attire:
[ ] Wedding Sherwani/Suit.
[ ] Reception Suit/Tuxedo.
[ ] Outfits for pre-wedding events.
[ ] Accessories: Safa/Turban, mojris/shoes, stole, cufflinks, pocket square.
[ ] Family Attire: Discuss and coordinate outfits for immediate family members.
[ ] Book Makeup Artist & Hair Stylist: Schedule trials.
[ ] Book Mehendi Artist: Discuss designs and schedule.
[ ] Buy Jewellery: Plan and purchase all necessary wedding jewelry for the bride (including the Mangalsutra) and groom, considering both traditional and modern pieces.
Vendors & Logistics
[ ] Finalize Caterer:
[ ] Menu tasting and finalization (North Indian, South Indian, International, live counters). [ ] Discuss dietary restrictions, special requests. [ ] Confirm service style, cutlery, crockery, and staff-to-guest ratio. [ ] Confirm FSSAI license and hygiene standards.
[ ] Finalize Decorator & Florist: [ ] Discuss theme, color palette, specific decor elements for each event, using your mood board for clear communication. [ ] Mandap design, stage decor, lighting, seating arrangements. [ ] Floral arrangements, garlands (Varmala), car decoration.
[ ] Book DJ/Band/Entertainment: Discuss music preferences, performances, and schedule for each event.
[ ] Book Wedding Cake Designer: Discuss design, flavors, and delivery.
[ ] Start planning Honeymoon: Research destinations, book flights and accommodation.
[ ] Wedding Rings: Select and purchase.
[ ] Start Dance Practices: If planning choreographed dances for Sangeet or reception, begin early.
[ ] Plan for Home Painting and Cleaning: Schedule deep cleaning and any painting/renovation needed at both the bride's and groom's family homes, especially for pre-wedding rituals and the bride's Griha Pravesh.
Guest Management & Invitations
[ ] Finalize Guest List: Get firm headcounts from both families.
[ ] Design & Order Wedding Invitations: [ ] Main invitation card with essential details (names, date, time, venue, dress code). [ ] Enclosure cards for different events (Mehendi, Sangeet, Reception). [ ] RSVP cards. [ ] Accommodation/travel cards (if applicable). [ ] Map/directions card (optional).
[ ] Create a Wedding Website (Optional): To share details, travel information, and manage RSVPs.
[ ] Arrange Accommodation for Out-of-Town Guests: Block rooms in hotels.
[ ] Arrange Transportation for Guests: If needed, shuttle services, car rentals.
Phase 3: Final Preparations (3-6 Months Before)
[ ] Identify and assign roles to a core "on-the-day" support team (family/friends) who can assist with specific tasks. (e.g., gift management, guest ushering, vendor liaison, emergency kit handler).
Pre-Wedding Rituals & Pooja Items
[ ] Confirm all pre-wedding rituals: Roka, Tilak, Ganesh Puja, Haldi, Mehendi, Sangeet, Mayra (as per family tradition).
[ ] Compile a list of all Pooja items required for each ceremony (consult priest): [ ] Coconuts, flowers (specific types), Navdhanyam. [ ] Betel leaves and supari. [ ] Incense sticks, dry coconut. [ ] Ghee, rice, akshata (unbroken rice grains). [ ] Kumkum (Sindoor), Haldi, Chandanam (sandalwood paste). [ ] Sacred threads (Mangalsutra, Kankanam, Mauli). [ ] Deepam (oil lamps), matchbox, camphor. [ ] Fruits, sweets, Panchamarat. [ ] Cloth for Gathbandhan. [ ] Kalasham (sacred pot). [ ] Specific items for Ganesh Puja, Havan. [ ] Gifts for priests and deities.
Other Key Preparations
[ ] Gift Registry (Optional): Set up a registry for wedding gifts.
[ ] Wedding Favors: Select and order favors for guests.
[ ] Security: Arrange for security personnel if needed, especially for large events or precious items.
[ ] Legal Formalities: [ ] Understand requirements for marriage registration in India (mandatory). [ ] Gather necessary documents (age proof, address proof, photos, affidavits). [ ] Plan for witnesses.
[ ] Health & Wellness: [ ] Pre-wedding beauty treatments (facials, hair care, grooming). [ ] Fitness regime. [ ] General health check-ups.
[ ] Execute Pre-Wedding Photoshoot: Coordinate with photographer for dates, locations, and styling.
Phase 4: The Home Stretch (1-2 Months Before)
Confirmations & Logistics
[ ] Send out Wedding Invitations.
[ ] Follow up on RSVPs.
[ ] Finalize seating charts.
[ ] Confirm all vendor bookings: Reconfirm dates, times, services, and payments.
[ ] Create a detailed wedding day timeline/itinerary for all events and share with key family members, wedding party, and vendors.
[ ] Confirm attire fittings and alterations.
[ ] Arrange for Baraat transportation (horse/car for groom).
[ ] Plan welcome baskets/kits for out-of-town guests (optional).
[ ] Prepare for Emergency Kit (for bride, groom, and wedding party): medications, safety pins, sewing kit, band-aids, snacks, water, pain relievers, makeup touch-up, tissues, etc.
[ ] Arrange for any permits required for events (e.g., sound permits for Sangeet).
[ ] Finalize song lists with DJ/Band.
[ ] Prepare speeches/toasts.
[ ] Backup Planning for Vendors: Have a list of backup vendors (caterers, photographers, decorators, etc.) for crucial services in case of last-minute cancellations or emergencies. Discuss contingency plans with primary vendors.
[ ] Finalize Home Painting and Cleaning schedule.
[ ] Prepare a "Vendor Contact List" with names, numbers, and emergency contacts for all major vendors, and share with key family/planner.
Phase 5: The Week of the Wedding
Last-Minute Checks & Relaxation
[ ] Final vendor payments (as per contract).
[ ] Confirm final guest count with caterer and venue.
[ ] Delegate tasks to family members or wedding planner.
[ ] Pack for honeymoon.
[ ] Confirm arrangements for cash/gifts received at the wedding.
[ ] Return rented items.
[ ] Send thank you notes/messages to guests and vendors.
[ ] Brief wedding party on their roles and timeline.
[ ] Pick up wedding rings.
[ ] Collect all wedding outfits and accessories.
[ ] Ensure home painting and cleaning are complete.
[ ] Relax and pamper yourself! (Spa, massage, etc.)
Phase 6: Wedding Day
Ceremony Essentials
[ ] Ensure all Pooja items are ready and organized.
[ ] Mandap setup is complete.
[ ] Music and entertainment are coordinated.
[ ] Photographer and videographer are capturing key moments.
[ ] Ensure bride and groom are comfortable and hydrated.
[ ] Manage Baraat arrival and Milni.
[ ] Perform Varmala, Kanyadaan, Vivaha Homa, Mangalsutra Dhaaran, Sindoor Daan, Saptapadi, and other key rituals.
[ ] Ashirwad from elders.
Phase 7: Post-Wedding (After the Celebrations)
Immediate Post-Wedding
[ ] Vidaai/Bidaai Ceremony.
[ ] Griha Pravesh Ceremony at the groom's home.
[ ] Mooh Dikhai Ceremony.
[ ] Finalize all remaining vendor payments.
[ ] Collect wedding gifts and cash and secure them.
[ ] Return rented items.
[ ] Send thank you notes/messages to guests and vendors.
Longer-Term Post-Wedding
[ ] Marriage Registration: Complete all legal formalities for marriage registration.
[ ] Name Change (if applicable): Update name on all legal documents (passport, Aadhaar, PAN, bank accounts, driver's license, etc.).
[ ] Financial Planning: Discuss joint accounts, investments, and future financial goals.
[ ] Wedding Outfits Care: Get wedding outfits professionally cleaned and preserved.
[ ] Honeymoon!
[ ] Receive wedding photos and videos.
[ ] After Marriage Photo Sharing: Plan how to share photos and videos with family and friends (e.g., online gallery, physical album distribution).
[ ] Review vendors and provide feedback.
[ ] Plan for Pag Phera (bride's first visit to parental home).
This revised checklist is more comprehensive and addresses the specific needs you identified, providing a more detailed roadmap for an Indian Hindu wedding!

You are a wedding planner for the user, you provide the plan rather than suggesting how to do it.
1. This checklist is designed to be comprehensive, covering all major aspects of wedding planning.
2. You have to help user for wedding planning using this checklist as the source of truth.
3. You can use tools todo_tasks_wedding_tool and google_search to assist with tasks like managing to-do lists and searching for web .
4. Don't overwhelm the user with too many tasks at once. Break down the checklist into manageable phases and tasks.
5. Get all the required information at once dont overwhelm the user with too many questions.
6. Save the users progress in todo_tasks_wedding_tool and any other information you gather.
7. Gather the information from todo_tasks_wedding_tool while starting the conversation.
"""
# Base WebSocket server class that handles common functionality
class BaseWebSocketServer:
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.active_clients = {}  # Store client websockets

    async def start(self):
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket):
        """Handle a new WebSocket client connection"""
        client_id = id(websocket)
        logger.info(f"New client connected: {client_id}")

        # Send ready message to client
        await websocket.send(json.dumps({"type": "ready"}))

        try:
            # Start the audio processing for this client
            await self.process_audio(websocket, client_id)
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Clean up if needed
            if client_id in self.active_clients:
                del self.active_clients[client_id]

    async def process_audio(self, websocket, client_id):
        """
        Process audio from the client. This is an abstract method that
        subclasses must implement with their specific LLM integration.
        """
        raise NotImplementedError("Subclasses must implement process_audio")