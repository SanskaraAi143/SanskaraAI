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

curl -X GET "http://localhost:8765/wedding/3aa1f4fc-ce6c-47da-8d44-55b7c682146e"

curl -X POST "http://localhost:8765/onboarding/submit" \
-H "Content-Type: application/json" \
-d '{
  "wedding_id": "c677f8dd-e6d4-4161-8862-080a3d638738",
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
{
    "wedding_id": "7ee8840d-081e-4404-b368-b5dd8f68418b",
    "current_partner_details": {
        "name": "noah graham",
        "role": "Groom",
        "cultural_background": "andhra pradesh, rayalaseema, balija",
        "ceremonies": [
            "Sangeet",
            "Haldi"
        ],
        "budget_range": "4L",
        "priorities": [
            "Photography & Videography",
            "Guest Experience"
        ],
        "teamwork_agreement": true
    }
}


{
    "wedding_id": "c677f8dd-e6d4-4161-8862-080a3d638738",
    "current_partner_email": "sriramsismarriage@gmail.com",
    "other_partner_email": null,
    "current_partner_details": {
        "name": "noah graham ",
        "email": "sriramsismarriage@gmail.com",
        "role": "Groom",
        "cultural_background": "andhra, hindu",
        "ceremonies": [
            "Sangeet",
            "Haldi"
        ],
        "budget_range": "4L",
        "priorities": [
            "Photography & Videography",
            "Guest Experience"
        ],
        "teamwork_agreement": true
    }
}







curl -X POST "http://localhost:8765/onboarding/submit" \
-H "Content-Type: application/json" \
-d '{
  "wedding_details": {
    "wedding_name": "Puneeth & Piune Doe Wedding",
    "wedding_date": "2025-10-26",
    "wedding_location": "Bengaluru, India",
    "wedding_tradition": "Andhra Rayalaseema Style",
    "wedding_style": "Traditional Elegant"
  },
  "current_user_onboarding_details": {
    "name": "Puneeth ",
    "email": "kpuneeth714@gmail.com",
    "phone": "+1234567890",
    "role": "Groom",
    "cultural_background": "Andhra pradesh",
    "ceremonies": ["Haldi","pellikoduku"],
    "custom_instructions": "Focus on minimalist decor.",
    "teamwork_plan": {
      "venue_decor": "Bride",
      "catering": "Bride",
      "guest_list": "Bride",
      "sangeet_entertainment": "Bride"
    },
    "guest_estimate": "300-450",
    "guest_split": "50/50",
    "budget_range": "8L",
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
-d '
{
    "wedding_details": {
        "wedding_name": "puneeth & noah graham's Wedding",
        "wedding_date": "2025-08-28",
        "wedding_location": "Dharmavaram",
        "wedding_tradition": "",
        "wedding_style": "Grand & Traditional"
    },
    "current_user_onboarding_details": {
        "name": "puneeth",
        "email": "kpuneeth714@gmail.com",
        "phone": "07674051127",
        "role": "Bride",
        "cultural_background": "fsad (fds)",
        "ceremonies": [
            "Mehendi"
        ],
        "custom_instructions": "",
        "teamwork_plan": {
            "venue_decor": "Joint Effort",
            "catering": "Joint Effort",
            "guest_list": "Joint Effort",
            "sangeet_entertainment": "Joint Effort"
        },
        "guest_estimate": "400",
        "guest_split": "not sure",
        "budget_range": "8L",
        "budget_flexibility": "Flexible",
        "priorities": [
            "Food & Catering"
        ]
    },
    "partner_onboarding_details": {
        "name": "noah graham",
        "email": "sriramsismarriage@gmail.com"
    }
}

curl -X POST "http://localhost:8765/onboarding/submit" \
-H "Content-Type: application/json" \
-d '{
  "wedding_id": "7ee8840d-081e-4404-b368-b5dd8f68418b",
  "current_partner_details": {
    "name": "Piune Doe",
    "email": "sriramsismarriage@gmail.com",
    "role": "Bride",
    "cultural_background": "Telangana",
    "ceremonies": ["Haldi", "Pellikuthuru"],
    "budget_range": "7L",
    "priorities": ["Venue", "Catering", "Photography"],
    "teamwork_agreement": true
  }
}'

curl -X POST "http://localhost:8765/onboarding/submit" \
-H "Content-Type: application/json" \
-d '{
    "wedding_details": {
        "wedding_name": "Puneeth Kamatam & noah graham Wedding",
        "wedding_date": "2025-11-26",
        "wedding_location": "Bengaluru",
        "wedding_tradition": "",
        "wedding_style": "Modern & Minimalist"
    },
    "current_user_onboarding_details": {
        "name": "Puneeth Kamatam",
        "email": "kpuneeth714@gmail.com",
        "phone": "07674051127",
        "role": "Bride",
        "cultural_background": "andhra (balija)",
        "ceremonies": [
            "Mehendi"
        ],
        "custom_instructions": "",
        "teamwork_plan": {
            "venue_decor": "Joint Effort",
            "catering": "Joint Effort",
            "guest_list": "Joint Effort",
            "sangeet_entertainment": "Joint Effort"
        },
        "guest_estimate": "4333",
        "guest_split": "33",
        "budget_range": "3",
        "budget_flexibility": "Flexible",
        "priorities": [
            "Venue & Ambiance",
            "Food & Catering"
        ]
    },
    "partner_onboarding_details": {
        "name": "noah graham",
        "email": "sriramsismarriage@gmail.com"
    },
    "second_partner_submission": {
        "wedding_id": null,
        "current_partner_details": {},
        "partner_onboarding_details": {
            "name": "noah graham",
            "email": "sriramsismarriage@gmail.com"
        }
    }
}'


curl -X POST "http://localhost:8765/onboarding/submit" \
-H "Content-Type: application/json" \
-d '
{
    "wedding_details": {
        "name": "puneeth & noah graham's Wedding",
        "wedding_date": "2025-10-26",
        "wedding_location": "Dharmavaram",
        "wedding_tradition": "",
        "wedding_style": "Bohemian & Rustic"
    },
    "current_user_onboarding_details": {
        "name": "puneeth",
        "email": "kpuneeth714@gmail.com",
        "phone": "07674051127",
        "role": "Bride",
        "cultural_background": "andhra pradesh, rayalaseema (balija)",
        "ceremonies": [
            "Haldi",
            "Mehendi"
        ],
        "custom_instructions": "",
        "teamwork_plan": {
            "venue_decor": "Bride's Side",
            "catering": "Joint Effort",
            "guest_list": "Joint Effort",
            "sangeet_entertainment": "Joint Effort"
        },
        "guest_estimate": "400",
        "guest_split": "not sure",
        "budget_range": "8L",
        "budget_flexibility": "Flexible",
        "priorities": [
            "Food & Catering"
        ]
    },
    "partner_onboarding_details": {
        "name": "noah graham",
        "email": "sriramsismarriage@gmail.com"
    }
}