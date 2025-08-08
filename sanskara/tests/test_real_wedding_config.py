"""
Configuration for real wedding integration tests.
Update these values with actual wedding data for testing.
"""

# Real Wedding Test Data - Update these with actual values
REAL_WEDDING_CONFIGS = {
    "wedding_1": {
        "wedding_id": "236571a1-db81-4980-be99-f7ec3273881c",
        "bride_name": "Priya Sharma",
        "groom_name": "Arjun Patel",
        "wedding_date": "2024-12-15",
        "venue": "Grand Palace Hotel, Mumbai",
        "style": "Traditional Hindu",
        "color_scheme": "Red, Gold, Ivory",
        "ceremony_type": "Hindu Wedding",
        "budget": "₹25,00,000",
        "guest_count": 300,
        "season": "Winter"
    },
    "wedding_2": {
        "wedding_id": "wedding_2024_delhi_gupta_002", 
        "bride_name": "Aisha Gupta",
        "groom_name": "Vikram Singh",
        "wedding_date": "2024-11-20",
        "venue": "The Leela Palace, New Delhi",
        "style": "Royal Rajasthani",
        "color_scheme": "Maroon, Gold, Pink",
        "ceremony_type": "Punjabi Sikh Wedding",
        "budget": "₹35,00,000",
        "guest_count": 500,
        "season": "Winter"
    },
    "wedding_3": {
        "wedding_id": "wedding_2025_bangalore_iyer_003",
        "bride_name": "Meera Iyer", 
        "groom_name": "Karthik Rao",
        "wedding_date": "2025-01-10",
        "venue": "Palace Grounds, Bangalore",
        "style": "South Indian Traditional",
        "color_scheme": "Green, Gold, White",
        "ceremony_type": "Tamil Brahmin Wedding",
        "budget": "₹20,00,000", 
        "guest_count": 200,
        "season": "Winter"
    }
}

# Test Image Prompts for Different Wedding Styles
WEDDING_STYLE_PROMPTS = {
    "Traditional Hindu": {
        "mandap": "Traditional red and gold mandap with marigold decorations, sacred fire pit, ornate pillars",
        "decorations": "Traditional Indian wedding decorations with marigolds, roses, diyas, and rangoli patterns",
        "entrance": "Grand wedding entrance with traditional torans, flower garlands, and welcome gates"
    },
    "Royal Rajasthani": {
        "mandap": "Royal Rajasthani mandap with intricate carvings, mirror work, and regal draping",
        "decorations": "Rajasthani palace-style decorations with peacock motifs, jharokhas, and royal colors",
        "entrance": "Majestic Rajasthani entrance with elephant statues, royal umbrellas, and traditional architecture"
    },
    "South Indian Traditional": {
        "mandap": "South Indian kalyana mandapam with banana leaves, coconuts, traditional kolam patterns",
        "decorations": "South Indian wedding decorations with jasmine, lotus flowers, and traditional brass elements",
        "entrance": "Traditional South Indian entrance with mango leaves, coconut decorations, and kolam designs"
    },
    "Punjabi Sikh": {
        "mandap": "Sikh gurdwara-style mandap with Guru Granth Sahib, white and gold decorations, Khanda symbol",
        "decorations": "Punjabi wedding decorations with sunflowers, white roses, and vibrant colors",
        "entrance": "Punjabi wedding entrance with bhangra-themed decorations and festive colors"
    }
}

# Test Categories for Mood Board Items
MOOD_BOARD_CATEGORIES = [
    "Mandap Designs",
    "Floral Arrangements", 
    "Entrance Decorations",
    "Stage Backdrops",
    "Table Settings",
    "Lighting Ideas",
    "Bridal Outfits",
    "Groom Attire",
    "Invitation Designs",
    "Mehendi Decorations",
    "Reception Decor",
    "Photography Ideas"
]

# Realistic Test Prompts
REALISTIC_PROMPTS = {
    "mandap_detailed": """Create a stunning wedding mandap for {bride_name} and {groom_name}'s {ceremony_type}.
    
    Design Requirements:
    - Style: {style}
    - Color Scheme: {color_scheme}
    - Venue: {venue}
    - Season: {season}
    
    The mandap should include:
    - Four ornate pillars with traditional carvings
    - Sacred fire pit (havan kund) in the center
    - Floral decorations appropriate for {season} season
    - Proper seating arrangement for bride and groom
    - Traditional elements reflecting {style} culture
    - Lighting suitable for the ceremony time
    
    Make it elegant, authentic, and photographically beautiful.""",
    
    "reception_stage": """Design an elegant reception stage for {bride_name} and {groom_name}.
    
    Requirements:
    - Style: {style} with modern luxury touches
    - Colors: {color_scheme}
    - Guest Count: {guest_count}
    - Venue: {venue}
    
    Include:
    - Backdrop with couple's names and wedding date
    - Appropriate lighting for photography
    - Floral arrangements and fabric draping
    - Stage layout for couple's seating
    - Cultural elements reflecting their tradition""",
    
    "floral_centerpiece": """Create beautiful wedding reception centerpieces for {bride_name} & {groom_name}.
    
    Specifications:
    - Style: {style}
    - Colors: {color_scheme}
    - Season: {season}
    - Table count: {guest_count} guests
    
    Design elegant table centerpieces featuring:
    - Seasonal flowers appropriate for {season}
    - Traditional elements from {style} culture
    - Candles or traditional lighting
    - Height variation for visual interest
    - Cost-effective design within budget constraints"""
}

# Test Configuration
TEST_CONFIG = {
    "use_real_api": False,  # Set to True to use real Gemini API
    "use_real_supabase": False,  # Set to True to use real Supabase storage
    "test_image_path": "/home/puneeth/programmes/Sanskara_AI/SanskaraAI/sanskara/gemini_generated_output.png",
    "max_concurrent_requests": 3,
    "timeout_seconds": 30
}
