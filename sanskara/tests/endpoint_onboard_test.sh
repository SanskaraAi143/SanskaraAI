curl -X POST "http://localhost:8765/onboarding/submit" \
-H "Content-Type: application/json" \
-d '{
  "wedding_details": {
    "wedding_name": "John & Jane Doe Wedding",
    "wedding_date": "2025-10-26",
    "wedding_location": "New York, NY",
    "wedding_tradition": "Western",
    "wedding_style": "Modern Elegant"
  },
  "current_user_onboarding_details": {
    "name": "John Doe",
    "email": "kpuneeth714@gmail.com",
    "phone": "+1234567890",
    "role": "Groom",
    "cultural_background": "American",
    "ceremonies": ["Ceremony", "Reception"],
    "custom_instructions": "Focus on minimalist decor.",
    "teamwork_plan": {
      "venue_decor": "Joint Effort",
      "catering": "John handles",
      "guest_list": "Jane handles",
      "sangeet_entertainment": "N/A"
    },
    "guest_estimate": "100-150",
    "guest_split": "50/50",
    "budget_range": "50k-70k",
    "budget_flexibility": "Flexible",
    "priorities": ["Venue", "Catering", "Photography"]
  },
  "partner_onboarding_details": {
    "name": "Jane Doe",
    "email": "sriramsismarriage@gmail.com"
  }
}'


curl -X POST "http://localhost:8765/onboarding/submit" \
-H "Content-Type: application/json" \
-d '{
  "wedding_id": "9ce1a9c6-9c47-47e7-97cc-e4e222d0d90c",
  "current_partner_details": {
    "name": "Janew Doe",
    "email": "sriramsismarriage@gmail.com",
    "role": "Bride",
    "cultural_background": "American",
    "ceremonies": ["Ceremony", "Reception"],
    "budget_range": "50k-70k",
    "priorities": ["Venue", "Catering", "Photography"],
    "teamwork_agreement": true
  }
}'