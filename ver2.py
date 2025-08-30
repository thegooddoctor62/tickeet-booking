import asyncio
import os
import datetime
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, expect

# --- Setup and Configuration ---

# Set up a logging system to track the script's progress and errors
os.makedirs("logs/screenshots", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/booking.log"),
        logging.StreamHandler(),
    ],
)

# --- Automation Functions ---

async def navigate_to_search_results(page, from_city, to_city, date_str):
    """
    Constructs the search URL and navigates directly to the bus search results page.
    """
    logging.info("Building and navigating to the search results page directly.")

    # The city IDs for Bangalore and Palakkad are known from previous analysis
    from_city_value = f"298|{from_city}"
    to_city_value = f"462|{to_city}"
    
    # Example URL: https://onlineksrtcswift.com/search?fromCity=298%7CBangalore&toCity=462%7CPalakkad&departDate=28-09-2025&mode=oneway&src=h&stationInFromCity=&stationInToCity=
    search_url = (
        f"https://onlineksrtcswift.com/search?fromCity={from_city_value}"
        f"&toCity={to_city_value}"
        f"&departDate={date_str}"
        "&mode=oneway&src=h&stationInFromCity=&stationInToCity="
    )

    await page.goto(search_url, timeout=60000)
 
async def select_bus_and_seats(page, bus_provider_name):
    """
    Finds a specific bus by its provider name and clicks 'Select Seats'.
    """
    logging.info(f"Searching for bus provided by: '{bus_provider_name}'...")
    
    # This selector finds the parent div (the bus card) that contains the bus name
    bus_card = page.locator("div.srch-card", has=page.locator(f":text('{bus_provider_name}')")).first
    
    # Within that card, find the 'Select Seats' button and click it
    logging.info("Bus card found. Clicking 'Select Seats' button.")
    await bus_card.locator(".selectbutton").click()

async def select_seats(page, bus_card, seat_priority=[3, 5, 4, 6], max_seats=1):
    logging.info("Searching for available seats...")

    # ✅ Locate the seat chart like we did bus_card
    seat_chart = bus_card.locator("div.seatchart", has=page.locator("div.seat-wrap >> div.seats"))

    try:
        await seat_chart.wait_for(timeout=15000)
        logging.info("Seat chart found. Checking for available seats.")
    except:
        logging.error("Seat chart not found.")
        return

    selected_seats = 0

    # ✅ Loop through priority seats
    for seat_num in seat_priority:
        if selected_seats >= max_seats:
            break

        # ✅ Use 'has' logic for each seat inside the seat chart
        seat_locator = seat_chart.locator(
            "div.seatlook",
            has=page.locator(f"div.farepopup:has-text('Seat: {seat_num}')")
        )

        if await seat_locator.count() > 0:
            logging.info(f"Selecting seat {seat_num}")
            await seat_locator.first.click()
            selected_seats += 1
        else:
            logging.info(f"Seat {seat_num} not available.")

    if selected_seats == 0:
        logging.warning("No priority seats were selected.")
    else:
        logging.info(f"Selected {selected_seats} seat(s).")


# --- Main Orchestration Function ---

async def main():
    """
    Main function to orchestrate the first step of the booking process.
    """
    logging.info("Starting bus booking automation for KSRTC Swift.")

    # Hardcoded values
    FROM_CITY = "Bangalore"
    TO_CITY = "Palakkad"
    DATE_STR = "28-09-2025"
    BUS_PROVIDER = "PALAKKAD DEPOT"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        try:
            await navigate_to_search_results(page, FROM_CITY, TO_CITY, DATE_STR)
            
            bus_card = page.locator("div.srch-card", has=page.locator(f":text('{BUS_PROVIDER}')")).first
            
            # Find and select the bus
            await select_bus_and_seats(page, BUS_PROVIDER)
            await select_seats(page, bus_card)
            
            logging.info("SUCCESS: All steps completed successfully.")
            
        except PlaywrightTimeoutError:
            logging.error("Timeout occurred. The page structure might have changed.")
            await page.screenshot(path=f"logs/screenshots/step1_timeout_{int(datetime.datetime.now().timestamp())}.png")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            await page.screenshot(path=f"logs/screenshots/step1_failure_{int(datetime.datetime.now().timestamp())}.png")
        finally:
            await asyncio.sleep(100)
            await browser.close()
            logging.info("Automation session closed.")

if __name__ == "__main__":
    asyncio.run(main())
