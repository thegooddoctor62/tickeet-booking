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


async def main():
    """
    Main function to orchestrate the first step of the booking process.
    """
    logging.info("Starting bus booking automation for KSRTC Swift.")

    # Hardcoded values directly in the script as requested
    TARGET_URL = "https://onlineksrtcswift.com/"
    FROM_CITY = "Bangalore"
    TO_CITY = "Palakkad"

    # Launch a new browser instance
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        try:
            # 1. Navigate to the website
            logging.info(f"Navigating to {TARGET_URL}...")
            await page.goto(TARGET_URL, timeout=60000)

            # 2. Handle the promotional pop-up
            logging.info("Checking for and closing promotional messages...")
            try:
                # Based on the HTML you provided, we can target the close button
                # within the g-popup-close class.
                close_button = page.locator("a.g-popup-close")
                await close_button.click(timeout=10000)
                logging.info("Promotional pop-up closed successfully.")
            except PlaywrightTimeoutError:
                logging.info("No promotional pop-up found, continuing...")
            
            # Wait for the main booking form to be visible before proceeding
            await page.wait_for_selector('text=Book Bus Ticket', state='visible')

            # Use a smarter way to handle the pre-filled form
            logging.info("Swapping default 'From' and 'To' cities.")
            # Use the unique ID of the swap button
            await page.locator("#swap").click()

            # Now, fill the "To" city with the new value. The 'From' city is already set to 'Trivandrum'.
            logging.info(f"Changing 'To' city to: {TO_CITY}")
            await page.locator("#toCity_chosen input").fill(TO_CITY)
            
            # Use a more robust locator to click the correct list item from the search results
            await page.locator(".chosen-results li").get_by_text(TO_CITY).click()

            logging.info("SUCCESS: 'From' and 'To' cities selected.")
            
        except PlaywrightTimeoutError:
            logging.error("Timeout occurred. The page structure might have changed.")
            await page.screenshot(path=f"logs/screenshots/step1_timeout_{int(datetime.datetime.now().timestamp())}.png")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            await page.screenshot(path=f"logs/screenshots/step1_failure_{int(datetime.datetime.now().timestamp())}.png")
        finally:
            await browser.close()
            logging.info("Automation session closed.")



if __name__ == "__main__":
    asyncio.run(main())
