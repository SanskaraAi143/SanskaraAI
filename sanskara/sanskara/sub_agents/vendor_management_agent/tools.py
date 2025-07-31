from typing import Dict, Any, List, Optional

from sanskara.db_queries import (
    search_vendors_query,
    get_vendor_details_query,
    add_to_shortlist_query,
    create_booking_query,
    submit_review_query
)
from logger import json_logger as logger # Import the custom JSON logger
from sanskara.helpers import execute_supabase_sql
import asyncio

def search_vendors(category: str, city: str, budget_range: Optional[Dict[str, float]] = None, style_keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Searches the `vendors` table for suitable vendors based on category, city, budget, and style keywords.
    Args:
        category (str): The category of vendors to search for (e.g., "photographer", "caterer").
        city (str): The city where the vendors are located.
        budget_range (Optional[Dict[str, float]]): A dictionary with 'min' and/or 'max' keys for budget filtering.
        style_keywords (Optional[List[str]]): A list of keywords to match vendor styles or descriptions.
    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a vendor with their ID, name, and rating.
    """
    with logger.contextualize(tool_name="search_vendors", category=category, city=city, budget_range=budget_range, style_keywords=style_keywords):
        logger.debug(f"Entering search_vendors tool with category: {category}, city: {city}.")
        try:
            sql_query = search_vendors_query(
                category=category,
                city=city,
                budget_range=budget_range,
                style_keywords=style_keywords
            )
            result = asyncio.run(execute_supabase_sql(sql_query))
            
            if result.get("status") == "success" and result.get("data"):
                vendors = [{"vendor_id": vendor["vendor_id"], "name": vendor["vendor_name"], "rating": vendor.get("rating")} for vendor in result["data"]]
                logger.info(f"Found {len(vendors)} vendors for category: {category} in {city}.")
                return vendors
            logger.info(f"No vendors found for category: {category} in {city}.")
            return []
        except Exception as e:
            logger.error(f"Error in search_vendors: {e}", exc_info=True)
            return []


def get_vendor_details(vendor_id: str) -> Dict[str, Any]:
    """
    Fetches all details for a specific vendor from the `vendors` table.
    Args:
        vendor_id (str): The ID of the vendor to retrieve details for.
    Returns:
        Dict[str, Any]: A dictionary containing all details of the vendor.
    """
    with logger.contextualize(tool_name="get_vendor_details", vendor_id=vendor_id):
        logger.debug(f"Entering get_vendor_details tool for vendor_id: {vendor_id}.")
        try:
            sql_query = get_vendor_details_query(vendor_id=vendor_id)
            result = asyncio.run(execute_supabase_sql(sql_query))
            if result.get("status") == "success" and result.get("data"):
                vendor_details = result["data"][0] # Assuming vendor_id is unique
                logger.info(f"Successfully retrieved details for vendor_id: {vendor_id}.")
                return vendor_details
            logger.warning(f"No details found for vendor_id: {vendor_id}.")
            return {}
        except Exception as e:
            logger.error(f"Error in get_vendor_details for vendor_id: {vendor_id}: {e}", exc_info=True)
            return {}


def add_to_shortlist(wedding_id: str, linked_vendor_id: str, vendor_name: str, vendor_category: str) -> Dict[str, str]:
    """
    Adds a vendor to a user's shortlist in the `user_shortlisted_vendors` table.
    Args:
        wedding_id (str): The ID of the wedding for which the vendor is shortlisted.
        linked_vendor_id (str): The ID of the vendor to add to the shortlist.
        vendor_name (str): The name of the vendor.
        vendor_category (str): The category of the vendor.
    Returns:
        Dict[str, str]: A dictionary indicating the status of the operation.
    """
    with logger.contextualize(tool_name="add_to_shortlist", wedding_id=wedding_id, linked_vendor_id=linked_vendor_id):
        logger.debug(f"Entering add_to_shortlist tool for wedding_id: {wedding_id}, linked_vendor_id: {linked_vendor_id}.")
        try:
            sql_query = add_to_shortlist_query(
                wedding_id=wedding_id,
                linked_vendor_id=linked_vendor_id,
                vendor_name=vendor_name,
                vendor_category=vendor_category
            )
            result = asyncio.run(execute_supabase_sql(sql_query))
            if result.get("status") == "success" and result.get("data"):
                user_vendor_id = result["data"][0].get("user_vendor_id")
                logger.info(f"Successfully added vendor {vendor_name} to shortlist for wedding {wedding_id}. UserVendorID: {user_vendor_id}")
                return {"status": "success", "user_vendor_id": user_vendor_id}
            logger.error(f"Failed to add vendor {vendor_name} to shortlist for wedding {wedding_id}. Result: {result}")
            return {"status": "failure"}
        except Exception as e:
            logger.error(f"Error in add_to_shortlist for wedding {wedding_id}, vendor {linked_vendor_id}: {e}", exc_info=True)
            return {"status": "failure", "message": "An unexpected error occurred during shortlisting."}


def create_booking(user_id: str, vendor_id: str, event_date: str, total_amount: float, advance_amount_due: float = 0.0, paid_amount: float = 0.0, booking_status: str = 'pending_confirmation') -> Dict[str, str]:
    """
    Creates a formal booking record in the `bookings` table.
    Args:
        wedding_id (str): The ID of the wedding for which the booking is made.
        user_id (str): The ID of the user making the booking.
        vendor_id (str): The ID of the vendor being booked.
        event_date (str): The date of the event for which the vendor is booked (ISO format).
        total_amount (float): The final agreed-upon total amount for the booking.
        advance_amount_due (float): The amount of advance payment due.
        paid_amount (float): The amount already paid.
        booking_status (str): The current status of the booking.
    Returns:
        Dict[str, str]: A dictionary indicating the booking ID or status.
    """
    with logger.contextualize(tool_name="create_booking", wedding_id=wedding_id, user_id=user_id, vendor_id=vendor_id):
        logger.debug(f"Entering create_booking tool for wedding_id: {wedding_id}, vendor_id: {vendor_id}.")
        try:
            sql_query = create_booking_query(
                user_id=user_id,
                vendor_id=vendor_id,
                event_date=event_date,
                total_amount=total_amount,
                advance_amount_due=advance_amount_due,
                paid_amount=paid_amount,
                booking_status=booking_status
            )
            result = asyncio.run(execute_supabase_sql(sql_query))
            if result.get("status") == "success" and result.get("data"):
                booking_id = result["data"][0].get("booking_id")
                logger.info(f"Successfully created booking for vendor {vendor_id} for wedding {wedding_id}. Booking ID: {booking_id}")
                return {"booking_id": booking_id}
            logger.error(f"Failed to create booking for vendor {vendor_id} for wedding {wedding_id}. Result: {result}")
            return {"status": "failure"}
        except Exception as e:
            logger.error(f"Error in create_booking for wedding {wedding_id}, vendor {vendor_id}: {e}", exc_info=True)
            return {"status": "failure", "message": "An unexpected error occurred during booking creation."}


def submit_review(booking_id: str, user_id: str, vendor_id: str, rating: float, comment: str) -> Dict[str, str]:
    """
    Writes a new review to the `reviews` table.
    Args:
        booking_id (str): The ID of the booking being reviewed.
        user_id (str): The ID of the user submitting the review.
        vendor_id (str): The ID of the vendor being reviewed.
        rating (float): The rating given to the vendor (e.g., 1.0 to 5.0).
        comment (str): The review comment.
    Returns:
        Dict[str, str]: A dictionary indicating the review ID or status.
    """
    with logger.contextualize(tool_name="submit_review", booking_id=booking_id, user_id=user_id, rating=rating):
        logger.debug(f"Entering submit_review tool for booking_id: {booking_id}, user_id: {user_id}, rating: {rating}.")
        try:
            sql_query = submit_review_query(
                booking_id=booking_id,
                user_id=user_id,
                vendor_id=vendor_id,
                rating=rating,
                comment=comment
            )
            result = asyncio.run(execute_supabase_sql(sql_query))
            if result.get("status") == "success" and result.get("data"):
                review_id = result["data"][0].get("review_id")
                logger.info(f"Successfully submitted review for booking {booking_id} by user {user_id}. Review ID: {review_id}")
                return {"review_id": review_id}
            logger.error(f"Failed to submit review for booking {booking_id} by user {user_id}. Result: {result}")
            return {"status": "failure"}
        except Exception as e:
            logger.error(f"Error in submit_review for booking {booking_id}, user {user_id}: {e}", exc_info=True)
            return {"status": "failure", "message": "An unexpected error occurred during review submission."}


if __name__ == "__main__":
    # test get vendor using id , add vendor to shortlist, create booking and submit review
    try:
        vendor_id = "20d9bbe1-994d-461c-9358-c810211787c4"
        user_id = "fca04215-2af3-4a4e-bcfa-c27a4f54474c"
        wedding_id = "9ce1a9c6-9c47-47e7-97cc-e4e222d0d90c"
        # print("=== Testing Get Vendor Details ===")
        # vendor_details = get_vendor_details(vendor_id)
        # print(f"Vendor Details: {vendor_details}")
        # print("\n=== Testing Add to Shortlist ===")
        # shortlist_result = add_to_shortlist(wedding_id, vendor_id, vendor_details.get("vendor_name", "Unknown Vendor"), vendor_details.get("category", "Unknown Category"))
        # print(f"Shortlist Result: {shortlist_result}")
        # print("\n=== Testing Create Booking ===")
        # booking_result = create_booking(
        #     wedding_id=wedding_id,
        #     user_id=user_id,
        #     vendor_id=vendor_id,
        #     event_date="2024-12-25",
        #     total_amount=5000.0,
        #     advance_amount_due=1000.0,
        #     paid_amount=500.0,
        #     booking_status="pending_confirmation"
        # )
        # print(f"Booking Result: {booking_result}")
        # print("\n=== Testing Submit Review ===")
        review_result = submit_review(
            booking_id="6615ff38-bd82-465a-b915-32c4350c9cc7",
            user_id=user_id,
            vendor_id=vendor_id,
            rating=4.5,
            comment="Great service and very professional!"
        )
        print(f"Review Result: {review_result}")
        # print("\n=== Testing Search Vendors ===")
        # vendors = search_vendors(
        #     category="caterer",
        #     city="Bangalore",
        #     budget_range={"min": 2000, "max": 10000},
        #     style_keywords=["Indian", "Vegetarian"]
        # )
        # print(f"Found Vendors: {vendors}")
    except Exception as e:
        logger.error(f"An error occurred during testing: {e}", exc_info=True)
    finally:
        logger.info("Vendor management agent tests completed.")