# seed_vault/ui/components/continuous_waveform.py

from typing import List
import streamlit as st
from datetime import datetime
from copy import deepcopy
import threading
import sys
import time
import queue
from html import escape
from seed_vault.models.config import SeismoLoaderSettings
from seed_vault.service.seismoloader import run_continuous
from seed_vault.ui.components.display_log import ConsoleDisplay
from seed_vault.service.utils import convert_to_datetime, get_time_interval, shift_time, parse_inv
from seed_vault.ui.app_pages.helpers.common import save_filter

# Create a global stop event for cancellation
stop_event = threading.Event()
# Create a global queue for logs
log_queue = queue.Queue()

class ContinuousFilterMenu:
    def __init__(self, settings: SeismoLoaderSettings):
        self.settings = settings
        self.old_settings = deepcopy(settings)
        # Track previous time state
        self.old_time_state = {
            'start_time': self.settings.station.date_config.start_time,
            'end_time': self.settings.station.date_config.end_time
        }
        self.last_button_pressed = None
        self.todo_nets = None

    def refresh_filters(self):
        """Check for changes and trigger updates"""
        current_time_state = {
            'start_time': self.settings.station.date_config.start_time,
            'end_time': self.settings.station.date_config.end_time
        }
        
        # Check if time state changed - use deep comparison for datetime objects
        # it doesn't seem to stay updated always.. possible not working correctly in __init__
        time_changed = (current_time_state['start_time'] != self.old_time_state['start_time'] or 
                       current_time_state['end_time'] != self.old_time_state['end_time'])
        
        if time_changed:
            self.old_time_state = {
                'start_time': current_time_state['start_time'],
                'end_time': current_time_state['end_time']
            }
            save_filter(self.settings)
            st.rerun()

        # Check if other settings changed
        changes = self.settings.has_changed(self.old_settings)
        if changes.get('has_changed', False):
            self.old_settings = deepcopy(self.settings)
            save_filter(self.settings)
            st.rerun()

    def refresh_filters_OLD(self):
        """Check for changes and trigger updates"""
        current_time_state = {
            'start_time': self.settings.station.date_config.start_time,
            'end_time': self.settings.station.date_config.end_time
        }
        
        # Check if time state changed
        if current_time_state != self.old_time_state:
            self.old_time_state = current_time_state.copy()
            save_filter(self.settings)
            st.rerun()

        # Check if settings changed
        changes = self.settings.has_changed(self.old_settings)
        if changes.get('has_changed', False):
            self.old_settings = deepcopy(self.settings)
            save_filter(self.settings)
            st.rerun()

    def render(self):
        st.sidebar.title("Download Parameters")

        # debugging
        #st.sidebar.write("Current start time:", self.settings.station.date_config.start_time)
        #st.sidebar.write("Old start time:", self.old_time_state['start_time'])
        #st.sidebar.write("Current end time:", self.settings.station.date_config.end_time)
        #st.sidebar.write("Old end time:", self.old_time_state['ed_time'])

        ## Get the list of items about to be downloaded
        # ...For some reason this snippet only works in render
        #    & we don't want to re-run it needlessly
        if not self.todo_nets:
            self.todo_nets,self.todo_stas,self.todo_locs,self.todo_chas = \
            parse_inv(self.settings.station.selected_invs)
        
        with st.sidebar.expander("Adjust Time Range?", expanded=True):
            start_date, start_time = convert_to_datetime(self.settings.station.date_config.start_time)
            end_date, end_time = convert_to_datetime(self.settings.station.date_config.end_time)


            # Row 1: Year controls
            col1, col2, col3, col4 = st.columns(4)
            # Row 2: Month controls
            col5, col6, col7, col8 = st.columns(4)
            # Row 3: Week controls
            col9, col10, col11, col12 = st.columns(4)
            # Row 4: Day controls
            #col13, col14, col15, col16 = st.columns(4)
            
            # Year controls
            with col1:
                if st.button("- Year", key="start-year-minus"):
                    self.settings.station.date_config.start_time = shift_time(
                        self.settings.station.date_config.start_time, 'year', -1)
                    self.refresh_filters()
            
            with col2:
                if st.button("+ Year", key="start-year-plus"):
                    self.settings.station.date_config.start_time = shift_time(
                        self.settings.station.date_config.start_time, 'year', 1)
                    self.refresh_filters()
            with col3:
                if st.button("-Year", key="end-year-minus"):
                    self.settings.station.date_config.end_time = shift_time(
                        self.settings.station.date_config.end_time, 'year', -1)
                    self.refresh_filters()
            
            with col4:
                if st.button("+Year", key="end-year-plus"):
                    self.settings.station.date_config.end_time = shift_time(
                        self.settings.station.date_config.end_time, 'year', 1)
                    self.refresh_filters()                   
            
            # Month controls
            with col5:
                if st.button("-Month", key="start-month-minus"):
                    self.settings.station.date_config.start_time = shift_time(
                        self.settings.station.date_config.start_time, 'month', -1)
                    self.refresh_filters()
            
            with col6:
                if st.button("+Month", key="start-month-plus"):
                    self.settings.station.date_config.start_time = shift_time(
                        self.settings.station.date_config.start_time, 'month', 1)
                    self.refresh_filters()
            with col7:
                if st.button("-Month", key="end-month-minus"):
                    self.settings.station.date_config.end_time = shift_time(
                        self.settings.station.date_config.end_time, 'month', -1)
                    self.refresh_filters()
            
            with col8:
                if st.button("+Month", key="end-month-plus"):
                    self.settings.station.date_config.end_time = shift_time(
                        self.settings.station.date_config.end_time, 'month', 1)
                    self.refresh_filters()                    
            
            # Week controls
            with col9:
                if st.button("-Week", key="start-week-minus"):
                    self.settings.station.date_config.start_time = shift_time(
                        self.settings.station.date_config.start_time, 'week', -1)
                    self.refresh_filters()
            
            with col10:
                if st.button("+Week", key="start-week-plus"):
                    self.settings.station.date_config.start_time = shift_time(
                        self.settings.station.date_config.start_time, 'week', 1)
                    self.refresh_filters()
            with col11:
                if st.button("-Week", key="end-week-minus"):
                    self.settings.station.date_config.end_time = shift_time(
                        self.settings.station.date_config.end_time, 'week', -1)
                    self.refresh_filters()
            
            with col12:
                if st.button("+Week", key="end-week-plus"):
                    self.settings.station.date_config.end_time = shift_time(
                        self.settings.station.date_config.end_time, 'week', 1)
                    self.refresh_filters()
            
            # Day controls
            """
            with col13:
                if st.button("- Day", key="start-day-minus"):
                    self.settings.station.date_config.start_time = shift_time(
                        self.settings.station.date_config.start_time, 'day', -1)
                    self.refresh_filters()
            
            with col14:
                if st.button("+ Day", key="start-day-plus"):
                    self.settings.station.date_config.start_time = shift_time(
                        self.settings.station.date_config.start_time, 'day', 1)
                    self.refresh_filters()
            with col15:
                if st.button("- Day", key="end-day-minus"):
                    self.settings.station.date_config.end_time = shift_time(
                        self.settings.station.date_config.end_time, 'day', -1)
                    self.refresh_filters()
            
            with col16:
                if st.button("+ Day", key="end-day-plus"):
                    self.settings.station.date_config.end_time = shift_time(
                        self.settings.station.date_config.end_time, 'day', 1)
                    self.refresh_filters()
            """


            c1, c2 = st.columns([1,1])
            with c1:
                new_start_date = st.date_input("Start Date", value=start_date)
                new_start_time = st.time_input("Start Time (UTC)", value=start_time)
                new_start = datetime.combine(new_start_date, new_start_time)
                if new_start != self.settings.station.date_config.start_time:
                    self.settings.station.date_config.start_time = new_start
                    self.last_button_pressed = None
                    self.refresh_filters()

            with c2:
                new_end_date = st.date_input("End Date", value=end_date)                
                new_end_time = st.time_input("End Time (UTC)", value=end_time)
                new_end = datetime.combine(new_end_date, new_end_time)
                if new_end != self.settings.station.date_config.end_time:
                    self.settings.station.date_config.end_time = new_end
                    self.last_button_pressed = None
                    self.refresh_filters()


            # also keep the last month/week/day options
            c21,c22,c23 = st.columns([1,1,1])
            with c21:
                if st.button('Last Month', key="station-set-last-month"):
                    end_time, start_time = get_time_interval('month')
                    self.settings.station.date_config.end_time = end_time
                    self.settings.station.date_config.start_time = start_time
                    self.refresh_filters()

            with c22:
                if st.button('Last Week', key="station-set-last-week"):
                    end_time, start_time = get_time_interval('week')
                    self.settings.station.date_config.end_time = end_time
                    self.settings.station.date_config.start_time = start_time
                    self.refresh_filters()

            with c23:
                if st.button('Last Day', key="station-set-last-day"):
                    end_time, start_time = get_time_interval('day')
                    self.settings.station.date_config.end_time = end_time
                    self.settings.station.date_config.start_time = start_time
                    self.refresh_filters()

        with st.sidebar.expander("Submitted NSLCs:", expanded=True):
            st.caption(f"Networks: {','.join(self.todo_nets)  if self.todo_nets else 'None'}")
            st.caption(f"Stations: {','.join(self.todo_stas)  if self.todo_stas else 'None'}")
            st.caption(f"Locations: {','.join([loc if loc != '' else '--' for loc in self.todo_locs]) if self.todo_locs else 'None'}")
            st.caption(f"Channels: {','.join(self.todo_chas)  if self.todo_chas else 'None'}")


class ContinuousDisplay:
    def __init__(self, settings: SeismoLoaderSettings, filter_menu: ContinuousFilterMenu):
        self.settings = settings
        self.filter_menu = filter_menu
        self.console = ConsoleDisplay()
        
    def process_continuous_data(self):
        """
        Fetches continuous waveform data in a background thread with logging.
        """
        # Custom stdout/stderr handler that writes to both the original streams and our queue
        class QueueLogger:
            def __init__(self, original_stream, queue):
                self.original_stream = original_stream
                self.queue = queue
                self.buffer = ""
            
            def write(self, text):
                self.original_stream.write(text)
                self.buffer += text
                if '\n' in text:
                    lines = self.buffer.split('\n')
                    for line in lines[:-1]:  # All complete lines
                        if line:  # Skip empty lines
                            self.queue.put(line)
                    self.buffer = lines[-1]  # Keep any partial line
                # Also handle case where no newline but we have content
                elif text and len(self.buffer) > 80:  # Buffer getting long, flush it
                    self.queue.put(self.buffer)
                    self.buffer = ""
            
            def flush(self):
                self.original_stream.flush()
                if self.buffer:  # Flush any remaining content in buffer
                    self.queue.put(self.buffer)
                    self.buffer = ""
        
        # Set up queue loggers
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = QueueLogger(original_stdout, log_queue)
        sys.stderr = QueueLogger(original_stderr, log_queue)
        
        try:
            # Print initial message to show logging is working
            print("Starting continuous waveform download process...")
            
            # Run the continuous download with stop_event for cancellation
            result = run_continuous(self.settings, stop_event)
            if result:
                success = True
                print("Download completed successfully.")
            else:
                success = False
                print("Download failed or was cancelled.")
        except Exception as e:
            success = False
            print(f"Error: {str(e)}")  # This will be captured in the output
        finally:
            # Flush any remaining content
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Restore original stdout/stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr

        st.session_state.update({
            "query_done": True,
            "is_downloading": False,
            "trigger_rerun": True
        })
        
    def render(self):
        st.title("Continuous Waveform Archiving")
        
        # Create three columns for the controls
        col1, col2 = st.columns(2)
        
        # Get Waveforms button in first column
        with col1:
            get_waveforms_button = st.button(
                "Download Waveforms",
                key="download_continuous",
                disabled=st.session_state.get("is_downloading", False),
                use_container_width=True
            )

        # Cancel Download button in second column
        with col2:
            if st.button("Cancel Download", 
                        key="cancel_continuous_download",
                        disabled=not st.session_state.get("is_downloading", False),
                        use_container_width=True):
                stop_event.set()  # Signal cancellation
                st.warning("Cancelling download...")
                st.session_state.update({
                    "is_downloading": False,
                    "polling_active": False
                })
                st.rerun()

        # Download status indicator
        status_container = st.empty()
        
        # Show appropriate status message
        if get_waveforms_button:
            status_container.info("Starting continuous waveform download...")
            self.retrieve_waveforms()
        elif st.session_state.get("is_downloading"):
            st.spinner("Downloading continuous waveforms... (this may take several minutes)")
            
            # Display real-time logs in the waveform view during download
            log_container = st.empty()
            
            # Process any new log entries from the queue
            new_logs = False
            while not log_queue.empty():
                try:
                    log_entry = log_queue.get_nowait()
                    if not self.console.accumulated_output:
                        self.console.accumulated_output = []
                    self.console.accumulated_output.append(log_entry)
                    new_logs = True
                except queue.Empty:
                    break
            
            # Save logs to session state if updated
            if new_logs or self.console.accumulated_output:
                st.session_state["log_entries"] = self.console.accumulated_output
                
                # Display logs in the waveform view
                if self.console.accumulated_output:
                    # Add the initial header line if it's not already there
                    if not any("Running run_continuous" in line for line in self.console.accumulated_output):
                        self.console.accumulated_output.insert(0, "Running run_continuous\n-----------------------")
                        st.session_state["log_entries"] = self.console.accumulated_output
                    
                    # Initialize terminal styling
                    self.console._init_terminal_style()
                    
                    escaped_content = escape('\n'.join(self.console.accumulated_output))
                    
                    log_text = (
                        '<div class="terminal" id="log-terminal" style="max-height: 400px; background-color: black; color: #ffffff; padding: 10px; border-radius: 5px; overflow-y: auto;">'
                        f'<pre style="margin: 0; white-space: pre; tab-size: 4; font-family: \'Courier New\', Courier, monospace; font-size: 14px; line-height: 1.4;">{escaped_content}</pre>'
                        '</div>'
                        '<script>'
                        'if (window.terminal_scroll === undefined) {'
                        '    window.terminal_scroll = function() {'
                        '        var terminalDiv = document.getElementById("log-terminal");'
                        '        if (terminalDiv) {'
                        '            terminalDiv.scrollTop = terminalDiv.scrollHeight;'
                        '        }'
                        '    };'
                        '}'
                        'window.terminal_scroll();'
                        '</script>'
                    )
                    
                    log_container.markdown(log_text, unsafe_allow_html=True)
        elif st.session_state.get("query_done"):
            status_container.success("Continuous data processing completed successfully!")

    def retrieve_waveforms(self):
        """
        Initiates waveform retrieval in a background thread with cancellation support
        """
        stop_event.clear()  # Reset cancellation flag
        st.session_state["query_thread"] = threading.Thread(target=self.process_continuous_data, daemon=True)
        st.session_state["query_thread"].start()

        st.session_state.update({
            "is_downloading": True,
            "query_done": False,
            "polling_active": True
        })

        st.rerun()

class ContinuousComponents:
    def __init__(self, settings: SeismoLoaderSettings):
        self.settings = settings
        self.filter_menu = ContinuousFilterMenu(settings)
        self.display = ContinuousDisplay(settings, self.filter_menu)
        self.console = ConsoleDisplay()
        
        # Initialize console with logs from session state if they exist
        if "log_entries" in st.session_state and st.session_state["log_entries"]:
            self.console.accumulated_output = st.session_state["log_entries"]
        
        # Pass console to ContinuousDisplay
        self.display.console = self.console
        
        # Initialize session state
        required_states = {
            "is_downloading": False,
            "query_done": False,
            "polling_active": False,
            "query_thread": None,
            "trigger_rerun": False,
            "log_entries": []
        }
        for key, val in required_states.items():
            if key not in st.session_state:
                st.session_state[key] = val
    
    def render_polling_ui(self):
        """
        Handles UI updates while monitoring background thread status
        """
        if st.session_state.get("is_downloading", False):
            query_thread = st.session_state.get("query_thread")
            
            # Process any new log entries from the queue
            new_logs = False
            while not log_queue.empty():
                try:
                    log_entry = log_queue.get_nowait()
                    if not self.console.accumulated_output:
                        self.console.accumulated_output = []
                    self.console.accumulated_output.append(log_entry)
                    new_logs = True
                except queue.Empty:
                    break
            
            # Save logs to session state if updated
            if new_logs:
                st.session_state["log_entries"] = self.console.accumulated_output
                # Trigger rerun to update the UI with new logs
                st.rerun()
            
            if query_thread and not query_thread.is_alive():
                try:
                    query_thread.join()
                except Exception as e:
                    st.error(f"Error in background thread: {e}")
                    # Add error to console output
                    if not self.console.accumulated_output:
                        self.console.accumulated_output = []
                    self.console.accumulated_output.append(f"Error: {str(e)}")
                    st.session_state["log_entries"] = self.console.accumulated_output

                st.session_state.update({
                    "is_downloading": False,
                    "query_done": True,
                    "query_thread": None,
                    "polling_active": False
                })
                st.rerun()

            # Always trigger a rerun while polling is active to check for new logs
            if st.session_state.get("polling_active"):
                time.sleep(0.2)  # Shorter pause for more frequent updates
                st.rerun()
        
    def render(self):
        # Initialize tab selection in session state if not exists
        if "continuous_active_tab" not in st.session_state:
            st.session_state["continuous_active_tab"] = 0  # Default to download tab
        
        # Auto-switch to log tab during download if new logs are available
        if st.session_state.get("is_downloading", False) and log_queue.qsize() > 0:
            st.session_state["continuous_active_tab"] = 0  # Keep on download tab to show real-time logs
        
        # Create tabs for Download and Log views
        tab_names = ["📊 Download View", "📝 Log View"]
        download_tab, log_tab = st.tabs(tab_names)
        
        # Always render filter menu (sidebar) first
        self.filter_menu.render()

        # Handle content based on active tab
        with download_tab:
            self.display.render()
            # Handle polling for background thread updates
            self.render_polling_ui()
        
        with log_tab:
            # If we're switching to log tab and download is complete, 
            # make sure all logs are transferred from queue to accumulated_output
            if not st.session_state.get("is_downloading", False):
                # Process any remaining logs in the queue
                while not log_queue.empty():
                    try:
                        log_entry = log_queue.get_nowait()
                        if not self.console.accumulated_output:
                            self.console.accumulated_output = []
                        self.console.accumulated_output.append(log_entry)
                    except queue.Empty:
                        break
                
                # Save to session state
                if self.console.accumulated_output:
                    st.session_state["log_entries"] = self.console.accumulated_output
            
            # Render log view
            st.title("Continuous Waveform Logs")
            
            if self.console.accumulated_output:
                # Initialize terminal styling
                self.console._init_terminal_style()
                
                # Display logs
                escaped_content = escape('\n'.join(self.console.accumulated_output))
                
                log_text = (
                    '<div class="terminal" id="log-terminal">'
                    f'<pre style="margin: 0; white-space: pre; tab-size: 4; font-family: \'Courier New\', Courier, monospace; font-size: 14px; line-height: 1.4;">{escaped_content}</pre>'
                    '</div>'
                    '<script>'
                    'if (window.terminal_scroll === undefined) {'
                    '    window.terminal_scroll = function() {'
                    '        var terminalDiv = document.getElementById("log-terminal");'
                    '        if (terminalDiv) {'
                    '            terminalDiv.scrollTop = terminalDiv.scrollHeight;'
                    '        }'
                    '    };'
                    '}'
                    'window.terminal_scroll();'
                    '</script>'
                )
                
                st.markdown(log_text, unsafe_allow_html=True)
            else:
                st.info("No logs available. Start a download to generate logs.")