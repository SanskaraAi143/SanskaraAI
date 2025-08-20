Excellent feedback. This level of detail is crucial for creating a truly personalized and culturally intelligent wedding planning assistant. The proposed changes shift the model from a generic planner to one that understands the nuanced, family-centric nature of Indian weddings, particularly regarding budget and responsibilities.
Here is the revised and more comprehensive "First Consultation" question flow, incorporating all your suggestions.
---
### **Revised Onboarding "First Consultation" Question Flow**
#### **Module 1: The Core Foundation (Setting the Stage)**
*   **Goal:** To establish who is planning, the key individuals, and the foundational details of the event.
1.  **The Couple & Your Role:**
	*   "To get started, could you please tell me your full name?"
	*   "And are you the **Bride** or the **Groom**?"
	*   "Perfect. What is your partner's full name and their email address? I'll send them a personalized invitation to join this planning space so you can collaborate on the tasks assigned to each of you."
1.  **The Event Basics:**
	*   "In which city and country will the main wedding events take place?"
	*   "Do you have a preferred wedding date in mind? You can select a specific date below."
		*   ***(UI Element: Interactive Calendar/Date Selector)***
	*   "Many families consult with a spiritual guide for the most auspicious date. Have you spoken with a _pujari_ or priest to fix a date and _muhurtham_ (the auspicious time)?"
	*   "If yes, could you please share the exact date and time of the muhurtham? This is crucial for booking the ceremony venue and coordinating with vendors."
1.  **The Guest Estimate:**
	*   "Let's get a sense of the celebration's size. What's your best estimate for the total number of guests you'll be inviting? A rough range is perfect for now (e.g., 100-150, 250-300)."
	*   "And roughly, how does that split between your side and your partner's side? (e.g., 'About half and half' or '150 from my side, 150 from theirs')."
#### **Module 2: The Vision & Vibe (The Look and Feel)**
*   **Goal:** To understand the aesthetic, which will guide all creative and vendor recommendations for the aspects you are managing.
4.  **The Overall Style:**
	*   "When you picture the events your family will be hosting, what's the overall feeling or style you're going for? You can choose from options like: **Grand & Traditional**, **Modern & Minimalist**, **Bohemian & Rustic**, **Intimate & Elegant**, or describe your own unique vision."
4.  **Inspiration & Mood:**
	*   "Do you have any specific colors or themes in mind? (e.g., 'Pastels and florals', 'Royal blue and gold')."
	*   **(Multi-modal)** "This is the perfect time to share inspiration! If you have photos from Pinterest, Instagram, or magazines that capture the look you love, feel free to upload them now. It will help me understand your style perfectly."
4.  **The Wedding Attire:**
	*   "Thinking about your own outfits, do you have a specific style or designer in mind for your main wedding ceremony attire?"
	*   "What about for the other events like the Sangeet or Reception? Are you thinking of a different look for each function?"
#### **Module 3: The Cultural Heartbeat (Rituals & Ceremonies)**
*   **Goal:** To map out the specific events your side of the family will host and demonstrate cultural understanding.
7.  **Family Backgrounds (with explanations):**
	*   "To help suggest the right traditions and vendors, could you share a bit more about your family's background? This helps me understand the specific rituals that might be important to you."
	*   **Region:** "Which state or region of India is your family from? (e.g., Punjab, Tamil Nadu, Gujarat, West Bengal). This often influences food, music, and specific customs."
	*   **Religion:** "What is your family's religion? (e.g., Hindu, Sikh, Muslim, Christian)."
	*   **Caste/Community (Optional):** "If relevant to your wedding traditions, would you like to share your caste or community? (e.g., Brahmin, Shetty, Marwari). This can sometimes influence specific puja rituals or pre-wedding ceremonies."
7.  **Ceremony Selection (For Your Side):**
	*   **(AI Proposes, User Confirms)** "Wonderful, thank you. Based on your background, here are the ceremonies your side of the family commonly hosts or plays a key part in: [_AI dynamically lists events like Mehendi, Haldi, Chooda Ceremony, Tilak, Ganesh Puja, etc._]. Are you planning to include all of these?"
	*   "Are there any other rituals you plan to host at home or at a separate venue? Feel free to add or remove any from this list."
#### **Module 4: The Teamwork Plan (Roles & Responsibilities)**
*   **Goal:** To proactively assign ownership of major planning areas before discussing the budget.
9.  **Task Delegation:**
	*   **(AI Proposes, User Assigns)** "Great planning is about teamwork. Let's decide which side will take the lead on a few key areas. For each, please assign it to the **Bride's Side**, the **Groom's Side**, or as a **Joint Effort**."
		*   "**Venue & Decor Selection**"
		*   "**Catering & Menu Decisions**"
		*   "**Guest List Management & Invitations**" _(Can be pre-set to 'Handle Own Sides')_
		*   "**Photography & Videography**"
		*   "**Sangeet Performances & Entertainment**"
		*   "**Logistics (Guest Travel & Accommodation)**"
#### **Module 5: Your Budget & Priorities**
*   **Goal:** To set realistic financial boundaries for the tasks your side is responsible for.
10. **The Budget (For Your Side):**
	*   "Now, let's talk about the budget for the responsibilities assigned to **your side**. Having a number in mind helps me find the best options for you. Do you have an estimated budget you're working with? A range is perfectly fine (e.g., '10-15 Lakhs', '25-30 Lakhs')."
	*   "Is this budget a strict limit, or is there some flexibility?"
10. **Top Priorities (For Your Side):**
	*   "Of the areas your side is responsible for (e.g., _Venue, Decor, Catering_), which **Top 2 or 3** are most important to you? This is where you'd be happy to allocate a larger portion of your budget. Common choices include:
		*   **Venue & Ambiance**
		*   **Food & Catering**
		*   **Photography & Videography**
		*   **Decor & Florals**
		*   **Guest Experience & Entertainment**"
---
### **Post-Onboarding Summary & Partner Invitation**
After the session, the AI provides a summary and outlines the next steps, including the separate onboarding for the partner.
> **AI:** "Thank you! That was incredibly helpful. Here’s a quick summary of the initial plan from your perspective:  **Event:** Your Wedding with [Partner's Name]  **When & Where:** [Date from selector] in [City], with the Muhurtham at [Time].  **Your Vibe:** [Style] with a [Color/Theme] theme.  **Your Ceremonies:** [List of confirmed ceremonies for the user's side].  **Your Responsibilities:** [List of tasks assigned to the user's side].  **Your Budget:** [Stated budget] with a focus on [Top 3 Priorities].**Next Steps:** **Inviting [Partner's Name]:** I have just sent an invitation to [Partner's Email]. They will have a separate onboarding session to confirm the details and responsibilities for their side. **Your Personalized Plan:** I've used your answers to create your initial to-do list, which you can see now. You can change any of this at any time."Based on your priorities, where would you like to start first? We could look at some stunning **venues**, explore some **caterers**, or browse **photographer portfolios**."
