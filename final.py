import asyncio
import os
import datetime
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, expect
import time

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

    await page.goto(search_url, timeout=6000)
 
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

    seat_chart = bus_card.locator("div.seatchart", has=page.locator("div.seat-wrap >> div.seats"))

    try:
        await seat_chart.wait_for(timeout=15000)
        logging.info("Seat chart found. Checking for available seats.")
    except:
        logging.error("Seat chart not found.")
        return

    selected_seats = 0
    all_seats = seat_chart.locator("div.seatlook")

    for seat_num in seat_priority:
        if selected_seats >= max_seats:
            break

        found_seat = None

        for i in range(await all_seats.count()):
            seat_div = all_seats.nth(i)
            text = await seat_div.text_content()

            # Skip sold seats
            if "Sold" in text:
                continue

            # Match exact seat number in farepopup
            fare_text = await seat_div.locator("div.farepopup").text_content()
            if fare_text and f"Seat: {seat_num} |" in fare_text:
                found_seat = seat_div
                break
        if found_seat:
            logging.info(f"Selecting seat {seat_num}")
            await found_seat.click()
            selected_seats += 1

            # Handle female seat confirmation for seats 3, 4, 5, 6
            try:
        # We locate the button by finding the 'alert' div inside the seat chart,
        # and then specifically finding the 'CONFIRM' div inside that.
                confirm_button = seat_chart.locator("div.alert--wrap--bottom >> div:has-text('CONFIRM')")
        
             # We use a 5-second timeout to give the pop-up time to appear and become clickable.
                await confirm_button.click(timeout=1000)
        
                logging.info("Confirmation button was successfully clicked.")

            except PlaywrightTimeoutError:
                logging.info("No confirmation pop-up was found, continuing...")
            except Exception as e:
                logging.error(f"An unexpected error occurred while clicking the button: {e}")

    if selected_seats == 0:
        logging.warning("No priority seats were selected.")
    else:
        logging.info(f"Selected {selected_seats} seat(s).")

async def select_pickup_point(bus_card, pickup_point_name):
    logging.info(f"Attempting to select pickup point: '{pickup_point_name}'")
    try:
        # First, find the seat chart locator from the bus_card
        seat_chart = bus_card.locator("div.seatchart", has=bus_card.locator("div.seat-wrap >> div.seats"))
        pickup_point = seat_chart.locator("div.point-opt.active >> div:has-text('Huskur gate')").first
        await pickup_point.click(timeout=1000)
        logging.info(f"Selected pickup point: {pickup_point_name}")
        
    except PlaywrightTimeoutError:
        logging.error(f"Pickup point '{pickup_point_name}' not found or dropdown did not appear.")
    except Exception as e:
        logging.error(f"An unexpected error occurred while selecting the pickup point: {e}")

async def select_dropoff_point(bus_card, dropoff_point_name):
    """
    Selects the specified dropoff point from the list.

    Args:
        bus_card: The Playwright locator for the bus card.
        dropoff_point_name: The name of the dropoff point to select (e.g., 'Palakkad').
    """
    logging.info(f"Attempting to select dropoff point: '{dropoff_point_name}'")
    try:

        seat_chart = bus_card.locator("div.seatchart", has=bus_card.locator("div.seat-wrap >> div.seats"))
        
        # Click the dropdown to show the list of pickup points
        #await seat_chart.locator(".pickups").click()
        await seat_chart.locator("div.point-inp.flex-vc", has_text=dropoff_point_name).click()
        # We use a specific locator that targets the active list of points
        # The new locator is more precise to avoid strict mode violations.
        pickup_point = seat_chart.locator("div.point-opt.active >> div.drop--val>>div:has-text('Palakkad')").first
        
        # Find the specific dropoff point by its class and text
        dropoff_point = seat_chart.locator("div.drop--val", has_text=dropoff_point_name)
        await dropoff_point.click(timeout=1000)
        await seat_chart.locator("div.pickups>>div.btnPassDetails", has_text="PROVIDE PASSENGER DETAILS").click()
        
        logging.info(f"Selected dropoff point: {dropoff_point_name}")
        
    except PlaywrightTimeoutError:
        logging.error(f"Dropoff point '{dropoff_point_name}' not found.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
async def enter_passenger_details(page, name, age, gender,number,email):
    logging.info("Entering passenger details.")
    try:
        # Find the name input field and fill it
        name_input = page.locator('input[placeholder="Name"]').first
        await name_input.fill(name)
        logging.info(f"Name entered: {name}")
        age_input = page.locator('input[name="paxAge[0]"]').first
        await age_input.fill(str(age))
        logging.info(f"Age entered: {age}")
        await page.locator("div.navswitchbtn.flex-all-c", has_text="PROCEED TO PAYEE DETAILS").click(timeout=1000)
        number_input = page.locator('input[name="mobileNo"]').first
        await number_input.fill(number)
        email_input = page.locator('input[name="email"]').first
        await email_input.fill(email)
        await page.locator("div.navswitchbtn.flex-all-c", has_text="PROCEED TO PAYMENT OPTIONS").click(timeout=1000)
    except PlaywrightTimeoutError:
        logging.error("Timeout occurred while entering passenger details.")
    except Exception as e:
        logging.error(f"An unexpected error occurred while entering passenger details: {e}")

async def enter_payee_details(page, upi_id):
    """
    Enters the payee details.

    Args:
        page: The Playwright page object.
        upi_id: The UPI ID to enter.
    """
    logging.info(f"Entering payee details: {upi_id}")
    try:
        # Find the input field using the label and fill it
        upi_input = page.locator("div.upi--input--wrap input")
        await upi_input.fill(upi_id)
        logging.info("UPI ID entered successfully.")
        await page.locator("div.flex-all-c.navswitchbtn ", has_text="VERIFY & PAY").click(timeout=1000)
    except PlaywrightTimeoutError:
        logging.error("Timeout occurred while locating the UPI ID field.")
    except Exception as e:
        logging.error(f"An unexpected error occurred while entering the UPI ID: {e}")

# --- Main Orchestration Function ---

async def main():
    """
    Main function to orchestrate the first step of the booking process.
    """
    logging.info("Starting bus booking automation for KSRTC Swift.")
    start_time = time.time()

    # Hardcoded values
    FROM_CITY = "Bangalore"
    TO_CITY = "Palakkad"
    DATE_STR = "28-09-2025"
    BUS_PROVIDER = "PALAKKAD DEPOT"
    PICKUP_POINT = "Huskur gate"
    DROPOFF_POINT = "Palakkad"
    NAME ="Anupama J"
    AGE="22"
    GENDER="Female"
    NUMBER="7025705845"
    EMAIL="anupamajayaprakash11@gmail.com"
    UPI_ID="7907158259@superyes"
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
            await select_pickup_point(page, PICKUP_POINT)
            await select_dropoff_point(page, DROPOFF_POINT)
            await enter_passenger_details(page,NAME,AGE,GENDER,NUMBER,EMAIL)
            await enter_payee_details(page,UPI_ID)

            
            end_time = time.time()
            elapsed_time = end_time - start_time
            logging.info(f"Total time taken to reach the last command: {elapsed_time:.2f} seconds.")
            
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
