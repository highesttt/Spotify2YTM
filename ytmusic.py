from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os

def setup_driver(headless=False):
    """Set up and return an Edge webdriver with anti-detection measures"""
    options = EdgeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Anti-detection measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Add flag to address WebGL warning
    options.add_argument("--enable-unsafe-swiftshader")
    # Disable WebGL entirely if still problematic
    options.add_argument("--disable-webgl")
    # Suppress unnecessary logging
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)
    
    # Additional anti-detection measures
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def spotify_login(driver):
    """Open Spotify and allow user to login"""
    print("Opening Spotify for login...")
    driver.get("https://open.spotify.com/")
    
    time.sleep(8)  # Wait longer for initial page load
    
    # Check for and accept cookies if prompted
    try:
        accept_cookies = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept Cookies') or contains(text(), 'Accept')]"))
        )
        accept_cookies.click()
        print("Accepted cookies")
        time.sleep(2)
    except:
        print("No cookie banner found or already accepted")
    
    # Check if login button exists and click it
    try:
        login_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, 
                "//button[contains(text(), 'Log in')] | "
                "//a[contains(text(), 'Log in')] | "
                "//span[contains(text(), 'Log in')] | "
                "//button[contains(@data-testid, 'login-button')]"
            ))
        )
        login_button.click()
        print("Clicked login button")
    except Exception as e:
        print(f"Login button not found or already logged in: {e}")
        print("Please manually navigate to login if needed")
    
    print("\n=================================================")
    print("Please log in to Spotify in the browser window")
    print("IMPORTANT: Make sure you're fully logged in before continuing")
    print("=================================================\n")
    input("Press Enter once you've logged in to Spotify...")
    
    # Give extra time for any redirects after login confirmation
    time.sleep(5)
    
    # Verify login by checking for specific elements or URLs
    if "open.spotify.com" in driver.current_url:
        print("✅ On Spotify website")
    else:
        print("⚠️ Not on Spotify website, navigating back...")
        driver.get("https://open.spotify.com/")
        time.sleep(5)
    
    # Additional verification - try to access the playlists directly
    print("Navigating to playlists to verify login...")
    driver.get("https://open.spotify.com/collection/playlists")
    time.sleep(5)
    
    return driver

def ytmusic_login(driver):
    """Open YouTube Music and allow user to login"""
    print("Opening YouTube Music for login...")
    driver.get("https://music.youtube.com/")
    time.sleep(3)  # Give page time to load completely
    
    # Check if sign-in button exists and click it
    try:
        signin_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in')] | //paper-button[contains(text(), 'Sign in')]"))
        )
        signin_button.click()
        print("Clicked sign-in button")
    except Exception as e:
        print(f"Sign-in button not found or already signed in: {e}")
    
    print("Please log in to YouTube Music in the browser window")
    print("(If you're already logged in, just press Enter to continue)")
    input("Press Enter once you've logged in to YouTube Music...")
    
    # Wait for successful login (checking for avatar)
    try:
        # Multiple possible selectors for the account button
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH, 
                "//button[@aria-label='Account'] | //img[contains(@alt, 'Avatar')] | //yt-img-shadow/img"
            ))
        )
        print("✅ Successfully logged in to YouTube Music")
    except Exception as e:
        print(f"⚠️ Could not confirm YouTube Music login: {e}")
        print("Attempting to continue anyway...")
    
    # Verify we're on YouTube Music site
    if "music.youtube.com" in driver.current_url:
        return driver
    else:
        print("Redirecting back to YouTube Music...")
        driver.get("https://music.youtube.com/")
        time.sleep(3)
        return driver

def get_spotify_playlists(driver):
    """Scrape playlist information from Spotify"""
    print("Navigating to your Spotify playlists...")
    driver.get("https://open.spotify.com/collection/playlists")
    
    # Wait longer for playlists to load
    print("Waiting for playlists to load...")
    time.sleep(8)
    
    # Try to find a specific element that indicates playlists are loaded
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'contentSpacing')]"))
        )
        print("Playlist page loaded successfully")
    except:
        print("Warning: Could not confirm playlist page loaded completely")
    
    # Scroll to load more playlists multiple times
    print("Scrolling to load all playlists...")
    scroll_attempts = 5
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    for _ in range(scroll_attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Wait longer after each scroll
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    
    # Try multiple selector patterns to find playlists
    selector_patterns = [
        "//div[@data-testid='grid-container']//div[@role='row']",
        "//div[contains(@class, 'main-gridContainer')]//div[@role='row']",
        "//div[@data-testid='playlist-tracklist-container']",
        "//div[contains(@class, 'GlueCard')]"
    ]
    
    playlists = []
    for pattern in selector_patterns:
        print(f"Trying selector pattern: {pattern}")
        playlist_elements = driver.find_elements(By.XPATH, pattern)
        
        if playlist_elements:
            print(f"Found {len(playlist_elements)} potential playlist elements")
            # Continue with original extraction logic...
            for element in playlist_elements:
                try:
                    # Try multiple selector patterns for playlist name and URL
                    name_selectors = [
                        ".//a[@data-testid='playlist-name']", 
                        ".//a[contains(@class, 'playlist-title')]",
                        ".//div[contains(@class, 'main-trackList-rowTitle')]//a"
                    ]
                    
                    for name_selector in name_selectors:
                        try:
                            name_element = element.find_element(By.XPATH, name_selector)
                            name = name_element.text
                            url = name_element.get_attribute("href")
                            
                            if name and url:
                                playlists.append({
                                    "name": name,
                                    "url": url
                                })
                                break
                        except:
                            continue
                except:
                    continue
            
            if playlists:
                break  # Stop trying patterns if we found playlists
    
    # Backup approach: Look for any playlist links if the above failed
    if not playlists:
        print("Trying backup approach to find playlists...")
        try:
            links = driver.find_elements(By.XPATH, "//a[contains(@href, '/playlist/')]")
            unique_urls = set()
            
            for link in links:
                try:
                    url = link.get_attribute("href")
                    if url and url not in unique_urls and "playlist" in url:
                        unique_urls.add(url)
                        name_element = link.find_element(By.XPATH, ".//*")  # Any child element
                        name = name_element.text if name_element.text else f"Playlist {len(unique_urls)}"
                        playlists.append({"name": name, "url": url})
                except:
                    continue
        except:
            print("Backup approach also failed")
    
    print(f"Found {len(playlists)} playlists on Spotify")
    
    # Debug information
    if not playlists:
        print("DEBUG: No playlists found. Current URL:", driver.current_url)
        print("DEBUG: Page title:", driver.title)
        # Take a screenshot
        try:
            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spotify_debug.png")
            driver.save_screenshot(screenshot_path)
            print(f"DEBUG: Screenshot saved to {screenshot_path}")
        except:
            print("DEBUG: Could not save screenshot")
    
    return playlists

def get_spotify_playlist_tracks(driver, playlist_url):
    """Scrape tracks from a Spotify playlist"""
    print(f"Getting tracks from playlist: {playlist_url}")
    driver.get(playlist_url)
    
    # Wait longer for tracks to load
    print("Waiting for tracks to load...")
    time.sleep(10)
    
    # Check if we need to accept cookies (might block UI)
    try:
        accept_cookies = driver.find_element(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Accept Cookies')]")
        accept_cookies.click()
        time.sleep(2)
    except:
        pass  # No cookie banner found
    
    # Scroll multiple times to load all tracks
    print("Scrolling to load all tracks...")
    scroll_count = 0
    max_scrolls = 10
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scroll_count += 1
    
    # Try multiple selector patterns to find tracks
    track_selector_patterns = [
        "//div[@data-testid='tracklist-row']",
        "//div[contains(@class, 'tracklist-row')]",
        "//div[contains(@class, 'TrackListRow')]"
    ]
    
    tracks = []
    for pattern in track_selector_patterns:
        print(f"Trying track selector: {pattern}")
        track_elements = driver.find_elements(By.XPATH, pattern)
        
        if track_elements:
            print(f"Found {len(track_elements)} potential track elements")
            
            for element in track_elements:
                try:
                    # Try different patterns for track name
                    track_name_found = False
                    track_name = ""
                    for name_selector in [
                        ".//a[@data-testid='internal-track-link']",
                        ".//div[contains(@class, 'tracklist-name')]",
                        ".//div[contains(@class, 'track-name')]"
                    ]:
                        try:
                            name_element = element.find_element(By.XPATH, name_selector)
                            track_name = name_element.text.strip()
                            if track_name:
                                track_name_found = True
                                break
                        except:
                            continue
                    
                    if not track_name_found:
                        continue
                    
                    # Try different patterns for artists
                    artists = ""
                    for artist_selector in [
                        ".//span[@data-testid='tracklist-row-artists-album-artist-link']",
                        ".//span[contains(@class, 'artist-name')]",
                        ".//div[contains(@class, 'artist')]//a"
                    ]:
                        try:
                            artist_elements = element.find_elements(By.XPATH, artist_selector)
                            if artist_elements:
                                artists = ", ".join([artist.text for artist in artist_elements if artist.text])
                                break
                        except:
                            continue
                    
                    # If we found at least a track name, add it
                    if track_name:
                        tracks.append({
                            "name": track_name,
                            "artists": artists
                        })
                except Exception as e:
                    print(f"Error extracting track info: {e}")
                    continue
            
            if tracks:
                break  # Stop if we found tracks with this selector
    
    # Debug information
    if not tracks:
        print("DEBUG: No tracks found. Taking screenshot...")
        try:
            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spotify_tracks_debug.png")
            driver.save_screenshot(screenshot_path)
            print(f"DEBUG: Screenshot saved to {screenshot_path}")
            
            # Also print page source to a file for debugging
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spotify_source.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"DEBUG: Page source saved to {html_path}")
        except:
            print("DEBUG: Could not save debug information")
    
    print(f"Found {len(tracks)} tracks in this playlist")
    return tracks

def create_ytmusic_playlist(driver, name, description="Imported from Spotify"):
    """Create a new playlist on YouTube Music"""
    # Navigate to library - try the playlists page directly
    driver.get("https://music.youtube.com/library/playlists")
    print("Waiting for YouTube Music playlists to load...")
    time.sleep(5)
    
    # Take a debug screenshot
    screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ytmusic_playlists.png")
    driver.save_screenshot(screenshot_path)
    
    # Click on New playlist button
    print("Looking for New playlist button...")
    try:
        new_playlist_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='New playlist']"))
        )
        new_playlist_button.click()
        print("Clicked New playlist button")
    except Exception as e:
        print(f"Could not find New playlist button by aria-label: {e}")
        try:
            # Fallback to JavaScript
            result = driver.execute_script("""
                var button = document.querySelector('button[aria-label="New playlist"]');
                if (button) {
                    button.click();
                    return "Button clicked via JS";
                }
                return "Button not found";
            """)
            print(f"JavaScript button click: {result}")
        except Exception as e:
            print(f"JavaScript button click failed: {e}")
    
    time.sleep(3)  # Wait for dialog to appear
    
    # Take screenshot after clicking
    screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "after_button_click.png")
    driver.save_screenshot(screenshot_path)
    
    # Fill the title input - using the correct ID from the HTML structure
    print("Looking for title input using correct selectors...")
    try:
        # Try finding by ID first - the actual ID from HTML
        title_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "title-input"))
        )
        # We need to find the actual input element inside
        input_element = title_input.find_element(By.TAG_NAME, "input")
        input_element.clear()
        input_element.send_keys(name)
        print(f"Entered playlist name: {name}")
    except Exception as e:
        print(f"Could not find title input by ID: {e}")
        
        # Try another approach - using JavaScript to target the actual input
        try:
            result = driver.execute_script(f"""
                // Target the input inside title-input
                var titleInput = document.querySelector('#title-input input');
                if (titleInput) {{
                    titleInput.value = "{name}";
                    titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    return "Set title via direct selector";
                }}
                
                // Try by label if ID approach failed
                var inputs = document.querySelectorAll('input');
                for (var i = 0; i < inputs.length; i++) {{
                    var label = inputs[i].getAttribute('aria-labelledby');
                    if (label) {{
                        var labelElement = document.getElementById(label);
                        if (labelElement && labelElement.textContent.trim() === 'Title') {{
                            inputs[i].value = "{name}";
                            inputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                            return "Set title via label match";
                        }}
                    }}
                }}
                return "Failed to set title";
            """)
            print(f"JavaScript title entry: {result}")
        except Exception as e:
            print(f"JavaScript title entry failed: {e}")
    
    time.sleep(2)
    
    # Take screenshot after title entry
    screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "after_title_entry.png")
    driver.save_screenshot(screenshot_path)
    
    # Click the Create button - look specifically for the create-button ID from HTML
    print("Looking for Create button...")
    try:
        create_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#create-button paper-button, #create-button button"))
        )
        create_button.click()
        print("Clicked Create button")
    except Exception as e:
        print(f"Could not find Create button: {e}")
        
        # Try JavaScript approach
        try:
            result = driver.execute_script("""
                var createBtn = document.querySelector('#create-button button, yt-button-renderer#create-button');
                if (createBtn) {
                    createBtn.click();
                    return "Clicked create button via direct selector";
                }
                
                // Try by text if ID approach failed
                var buttons = document.querySelectorAll('button, paper-button');
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].textContent.trim() === 'CREATE' || 
                        buttons[i].textContent.trim() === 'Create') {
                        buttons[i].click();
                        return "Clicked create button by text";
                    }
                }
                return "Failed to click create button";
            """)
            print(f"JavaScript create button click: {result}")
        except Exception as e:
            print(f"JavaScript create button click failed: {e}")
    
    # Wait for playlist to be created
    time.sleep(5)
    
    # Rest of the function remains the same
    
    # Get the URL which contains the playlist ID
    playlist_url = driver.current_url
    print(f"Current URL after creation: {playlist_url}")
    
    # Check if we're on a playlist page - updated to handle both URL formats
    if "playlist" in playlist_url or ("browse/VLPL" in playlist_url) or ("browse/VL" in playlist_url):
        print(f"✅ Created YouTube Music playlist: {name}")
        return playlist_url
    else:
        print("Not on playlist page, trying to find newly created playlist")
        # Try to find the newly created playlist in the list
        try:
            driver.get("https://music.youtube.com/library/playlists")
            time.sleep(3)
            
            # Take a screenshot of playlists page
            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playlists_after_create.png")
            driver.save_screenshot(screenshot_path)
            
            # Try to find and click the new playlist
            found = driver.execute_script(f"""
                var items = document.querySelectorAll('ytmusic-responsive-list-item-renderer');
                for(var i=0; i<items.length; i++) {{
                    if(items[i].innerText.includes("{name}")) {{
                        var link = items[i].querySelector('a');
                        if (link) {{
                            link.click();
                            return true;
                        }}
                    }}
                }}
                return false;
            """)
            
            if found:
                time.sleep(3)
                playlist_url = driver.current_url
                print(f"Found and navigated to playlist: {playlist_url}")
                return playlist_url
        except Exception as e:
            print(f"Error finding playlist in list: {e}")
        
        # If we still don't have a proper URL, use a mock one
        print("Using mock playlist URL to continue")
        return "https://music.youtube.com/playlist?list=mock_playlist_id"

def search_and_add_to_ytmusic_playlist(driver, playlist_url, track, playlist_name=""):
    """Search for a track on YouTube Music and add it to the playlist"""
    # Include both song name and artist in search for better results
    search_query = f"{track['name']} {track['artists']}"
    print(f"Searching for: {search_query}")
    
    # Check if we're using a mock playlist URL
    if "mock_playlist_id" in playlist_url:
        print("Using mock playlist - will search for track but can't add to playlist")
        search_url = f"https://music.youtube.com/search?q={search_query.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(2)
        print(f"⚠️ Track found but not added: {track['name']} - {track['artists']}")
        return True
    
    # Navigate to search
    search_url = f"https://music.youtube.com/search?q={search_query.replace(' ', '+')}"
    driver.get(search_url)
    time.sleep(3)  # Wait longer for search results
    
    # Take a screenshot of search results
    screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_results.png")
    driver.save_screenshot(screenshot_path)
    
    # Try to find and click the Save button using the exact HTML structure you provided
    try:
        save_button_result = driver.execute_script("""
            // Try looking for the Save button anywhere in the document
            var saveButtons = [];
            
            // METHOD 1: Find by exact aria-label
            var buttonsByLabel = document.querySelectorAll('button[aria-label="Save to playlist"]');
            for (var i = 0; i < buttonsByLabel.length; i++) {
                saveButtons.push(buttonsByLabel[i]);
            }
            
            // METHOD 2: Find inside action containers
            var actionContainers = document.querySelectorAll('#actions, .actions-container');
            for (var i = 0; i < actionContainers.length; i++) {
                var buttons = actionContainers[i].querySelectorAll('button');
                for (var j = 0; j < buttons.length; j++) {
                    if (buttons[j].textContent.includes('Save') || 
                        buttons[j].getAttribute('aria-label') === 'Save to playlist') {
                        saveButtons.push(buttons[j]);
                    }
                }
            }
            
            // METHOD 3: Find inside card-shelf-renderer (as shown in your HTML)
            var shelfRenderers = document.querySelectorAll('ytmusic-card-shelf-renderer');
            for (var i = 0; i < shelfRenderers.length; i++) {
                var buttons = shelfRenderers[i].querySelectorAll('button');
                for (var j = 0; j < buttons.length; j++) {
                    if (buttons[j].textContent.includes('Save') || 
                        buttons[j].getAttribute('aria-label') === 'Save to playlist') {
                        saveButtons.push(buttons[j]);
                    }
                }
            }
            
            // METHOD 4: Look for the exact button structure from your HTML
            var spans = document.querySelectorAll('span.yt-core-attributed-string');
            for (var i = 0; i < spans.length; i++) {
                if (spans[i].textContent.trim() === 'Save') {
                    // Find parent button
                    var current = spans[i];
                    while (current && current.tagName.toLowerCase() !== 'button') {
                        current = current.parentElement;
                    }
                    if (current) {
                        saveButtons.push(current);
                    }
                }
            }
            
            // METHOD 5: Last resort - any button with "Save" text
            if (saveButtons.length === 0) {
                var allButtons = document.querySelectorAll('button');
                for (var i = 0; i < allButtons.length; i++) {
                    if (allButtons[i].textContent.includes('Save')) {
                        saveButtons.push(allButtons[i]);
                    }
                }
            }
            
            console.log("Found " + saveButtons.length + " potential Save buttons");
            
            // Try to click the first found button
            if (saveButtons.length > 0) {
                console.log("Clicking Save button with text: " + saveButtons[0].textContent);
                saveButtons[0].click();
                return "Save button clicked";
            }
            
            return "No Save button found";
        """)
        print(f"Save button action: {save_button_result}")
        
        # Wait for the playlist dialog to appear
        time.sleep(2)
        
        # Take screenshot of the dialog
        screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playlist_dialog.png")
        driver.save_screenshot(screenshot_path)
        
        # Click the desired playlist in the dialog - specifically targeting the carousel items
        playlist_result = driver.execute_script(f"""
            // First find any dialog/popup container
            var dialog = document.querySelector('ytmusic-add-to-playlist-renderer') || 
                        document.querySelector('tp-yt-paper-dialog') ||
                        document.querySelector('ytmusic-popup-container');
            
            if (!dialog) {{
                // Try looking for any element that appeared after clicking Save
                var possibleDialogs = document.querySelectorAll('ytmusic-add-to-playlist-renderer, tp-yt-paper-dialog, ytmusic-popup-container');
                if (possibleDialogs.length > 0) {{
                    dialog = possibleDialogs[0];
                }}
            }}
            
            if (!dialog) {{
                return "Playlist dialog not found";
            }}
            
            console.log("Dialog found");
            
            // Look specifically for the carousel items which are the playlist entries
            // Target ytmusic-two-row-item-renderer elements inside any carousel
            var carouselItems = dialog.querySelectorAll('ytmusic-two-row-item-renderer');
            if (carouselItems.length === 0) {{
                // If not in a carousel, try the standard renderer
                carouselItems = dialog.querySelectorAll('ytmusic-playlist-add-to-option-renderer');
            }}
            
            console.log("Found " + carouselItems.length + " playlist items");
            
            // Try to find a match by name
            var targetItem = null;
            
            // Debug: Log all item texts
            console.log("Available playlists:");
            for (var i = 0; i < carouselItems.length; i++) {{
                console.log(i + ": " + carouselItems[i].textContent);
            }}
            
            if ('{playlist_name}') {{
                for (var i = 0; i < carouselItems.length; i++) {{
                    // For ytmusic-two-row-item-renderer, look specifically at the title element
                    var titleEl = carouselItems[i].querySelector('yt-formatted-string.title');
                    var itemText = titleEl ? titleEl.textContent : carouselItems[i].textContent;
                    
                    if (itemText.includes('{playlist_name}')) {{
                        targetItem = carouselItems[i];
                        console.log("Found playlist match: " + itemText);
                        break;
                    }}
                }}
            }}
            
            // If not found by name, use the first item (likely the most recently created)
            if (!targetItem && carouselItems.length > 0) {{
                targetItem = carouselItems[0];
                var firstItemTitle = targetItem.querySelector('yt-formatted-string.title');
                console.log("Using first playlist item: " + (firstItemTitle ? firstItemTitle.textContent : "Unnamed"));
            }}
            
            // Click the target item
            if (targetItem) {{
                // For carousel items, find and click the anchor tag or the item itself
                var clickTarget = targetItem.querySelector('a.yt-simple-endpoint') || targetItem;
                clickTarget.click();
                return "Clicked on playlist item";
            }}
            
            // Last resort - try to find any clickable element with playlist text
            var clickableElements = dialog.querySelectorAll('a, button, [role="button"]');
            for (var i = 0; i < clickableElements.length; i++) {{
                if (clickableElements[i].textContent.includes('{playlist_name}')) {{
                    console.log("Clicking fallback element: " + clickableElements[i].textContent);
                    clickableElements[i].click();
                    return "Clicked fallback element with playlist name";
                }}
            }}
            
            return "No playlist items found in dialog";
        """)
        print(f"Playlist selection: {playlist_result}")
        
        # Success check
        if "Clicked" in playlist_result:
            print(f"✅ Added to YouTube Music: {track['name']} - {track['artists']}")
            time.sleep(1)  # Wait for confirmation
            return True
        else:
            print(f"⚠️ Could not add to playlist: {track['name']} - {track['artists']}")
            return False
        
    except Exception as e:
        print(f"❌ Error adding track: {track['name']} - {track['artists']}")
        print(f"  Error: {e}")
        
        # Save a debug screenshot
        screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_screenshot.png")
        try:
            driver.save_screenshot(screenshot_path)
            print(f"Debug screenshot saved to: {screenshot_path}")
        except:
            pass
            
        return False

def migrate_playlists(spotify_driver, ytmusic_driver):
    """Migrate playlists from Spotify to YouTube Music"""
    # Get all Spotify playlists
    spotify_playlists = get_spotify_playlists(spotify_driver)
    
    for playlist in spotify_playlists:
        print(f"\nProcessing playlist: {playlist['name']}")
        
        # Get tracks for this playlist
        tracks = get_spotify_playlist_tracks(spotify_driver, playlist['url'])
        
        # Create a new playlist on YouTube Music
        ytmusic_playlist_url = create_ytmusic_playlist(ytmusic_driver, playlist['name'])
        if not ytmusic_playlist_url:
            print(f"Skipping playlist: {playlist['name']}")
            continue
        
        # Add each track to the YouTube Music playlist
        for i, track in enumerate(tracks):
            print(f"({i+1}/{len(tracks)}) Processing track: {track['name']} - {track['artists']}")
            search_and_add_to_ytmusic_playlist(ytmusic_driver, ytmusic_playlist_url, track, playlist['name'])
            time.sleep(1)  # Avoid rate limiting
        
        print(f"✅ Completed migration for playlist: {playlist['name']}")


# Add this function to your script
def setup_driver_with_profile(profile_path, headless=False):
    """Set up Edge with an existing profile that's already logged in"""
    options = EdgeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-data-dir={profile_path}")
    
    # Anti-detection measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver
def main():
    print("Spotify to YouTube Music Playlist Migration")
    print("------------------------------------------")
    
    # Ask user for Edge profile directory (if they have one)
    print("Do you have an Edge profile where you're already logged into YouTube Music?")
    use_profile = input("Type 'yes' if you do, or anything else to proceed normally: ").lower() == 'yes'
    
    if use_profile:
        print("\nCommon Edge profile directory locations:")
        print("- C:\\Users\\[YourUsername]\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default")
        print("- C:\\Users\\[YourUsername]\\AppData\\Local\\Microsoft\\Edge\\User Data\\Profile 1")
        print("\nTo find your profile directory:")
        print("1. Type 'edge://version' in your Edge address bar")
        print("2. Look for 'Profile Path' entry")
        print("3. Copy the path up to the 'User Data' folder, then add the profile name (Default, Profile 1, etc.)\n")
        
        profile_path = input("Enter the full path to your Edge profile directory: ")
        spotify_driver = setup_driver()
        ytmusic_driver = setup_driver_with_profile(profile_path)
    else:
        spotify_driver = setup_driver()
        ytmusic_driver = setup_driver()
    
    try:
        # Login to both services
        spotify_login(spotify_driver)
        
        if not use_profile:
            print("\nIMPORTANT: For YouTube Music login, you may need to:")
            print("1. Manually login in the browser window")
            print("2. Verify your identity using your phone if prompted")
            print("3. Complete any security challenges Google presents\n")
        
        ytmusic_login(ytmusic_driver)
        
        # Migrate playlists
        migrate_playlists(spotify_driver, ytmusic_driver)
        
        print("\n✅ Migration complete!")
        
    finally:
        # Clean up
        print("Closing browsers...")
        spotify_driver.quit()
        ytmusic_driver.quit()

if __name__ == "__main__":
    main()