import re
from pydantic import BaseModel
import json
from typing import IO, Dict, Optional, List, Tuple, Union, Any
from datetime import date, timedelta, datetime
from enum import Enum
import os
import configparser
from configparser import ConfigParser
import pickle

from obspy import UTCDateTime

from .common import RectangleArea, CircleArea
from seed_vault.enums.config import DownloadType, WorkflowType, GeoConstraintType, Levels, EventModels

# TODO: Not sure if these values are controlled values
# check to see if should we use controlled values or
# rely on free inputs from users.

from seed_vault.utils.clients import load_extra_client, load_original_client


# Convert start and end times to datetime
def parse_time(time_str):
    try:
        return UTCDateTime(time_str).isoformat()
    except:
        time_formats = [
            '%Y,%m,%d',         # Format like '2014,2,1'
            '%Y%j',             # Julian day format like '2014001'
            '%Y,%m,%d,%H,%M,%S' # Format with time '2014,3,2,0,0,5'
        ]
        for time_format in time_formats:
            try:
                return datetime.strptime(time_str, time_format)
            except ValueError:
                continue
    return None
    
def safe_add_to_config(config, section, key, value):
    """Helper function to safely add key-value pairs to config."""
    try:
        config[section][key] = convert_to_str(value)
    except Exception as e:
        print(f"Failed to add {key} to {section}: {e}")

def convert_to_str(val):
    try:
        if val is None:
            return ''  # Convert None to empty string
        if isinstance(val, Enum):
            return str(val.value)  # Convert Enum values to string
        if isinstance(val, (str, int, float, bool)):
            return str(val)  # Convert valid types to string
        if hasattr(val, '__str__'):
            return str(val)  # Use __str__ for objects
        return repr(val)  # Use repr for unsupported objects
    except Exception as e:
        print(f"Error converting value {val}: {e}")
        return ''  # Return empty string if conversion fails
            
class ProcessingConfig(BaseModel):
    num_processes: Optional    [  int         ] | None = 4
    gap_tolerance: Optional    [  int         ] | None = 60
    logging      : Optional    [  str         ] = None

class AuthConfig(BaseModel):
    nslc_code: str  # network.station.location.channel code
    username: str
    password: str

class SeismoQuery(BaseModel):
    network : Optional[str] = None
    station : Optional[str] = None
    location: Optional[str] = None
    channel : Optional[str] = None
    starttime: Optional[datetime] = None
    endtime: Optional[datetime] = None

    def __init__(self, cmb_str_n_s=None, **data):
        super().__init__(**data) 
        if cmb_str_n_s:
            self.cmb_str_n_s_to_props(cmb_str_n_s)

    @property
    def cmb_str(self):
        cmb_str = ''
        if self.network:
            cmb_str += f"{self.network}."
        if self.station:
            cmb_str += f"{self.station}."
        if self.location:
            cmb_str += f"{self.location}."
        if self.channel:
            cmb_str += f"{self.channel}."
        
        if cmb_str.endswith("."):
            cmb_str = cmb_str[:-1]

        return cmb_str
    
    def cmb_str_n_s_to_props(self, cmb_n_s):
        network, station = cmb_n_s.split(".")
        setattr(self, 'network', network)
        setattr(self, 'station', station)

class DateConfig(BaseModel):
    start_time  : Optional[Union[date, Any] ] = date.today() - timedelta(days=7)
    end_time    : Optional[Union[date, Any] ] = date.today()
    start_before: Optional[Union[date, Any] ] =      None
    start_after : Optional[Union[date, Any] ] =      None
    end_before  : Optional[Union[date, Any] ] =      None
    end_after   : Optional[Union[date, Any] ] =      None


class WaveformConfig(BaseModel):
    client           : Optional     [str]   = "IRIS"
    channel_pref     : Optional     [str]  = None
    location_pref    : Optional     [str] = None

    days_per_request : Optional     [int]             = 1

    def set_default(self):
        """Resets all fields to their default values."""
        self.__fields_set__.clear()
        for field_name, field in self.__fields__.items():
            setattr(self, field_name, field.get_default())

class GeometryConstraint(BaseModel):
    geo_type: Optional[GeoConstraintType] = GeoConstraintType.NONE
    coords: Optional[Union[RectangleArea, CircleArea]] = None

    def __init__(self, **data):
        super().__init__(**data)
        if isinstance(self.coords, RectangleArea):
            self.geo_type = GeoConstraintType.BOUNDING
        elif isinstance(self.coords, CircleArea):
            self.geo_type = GeoConstraintType.CIRCLE
        else:
            self.geo_type = GeoConstraintType.NONE


class StationConfig(BaseModel):
    client             : Optional   [ str] = "IRIS"
    force_stations     : Optional   [ List          [SeismoQuery]] = []
    exclude_stations   : Optional   [ List          [SeismoQuery]] = []
    date_config        : DateConfig                                = DateConfig(
        start_time=datetime(2024, 8, 20),
        end_time=datetime(2024, 9, 20)
    )
    local_inventory    : Optional   [ str           ] = None
    network            : Optional   [ str           ] = None
    station            : Optional   [ str           ] = None
    location           : Optional   [ str           ] = None
    channel            : Optional   [ str           ] = None
    selected_invs      : Optional   [Any] = None
    geo_constraint     : Optional   [ List          [GeometryConstraint]] = None
    include_restricted : bool       = False
    level              : Levels     = Levels        .CHANNEL

    class Config:
        json_encoders = {
            Any: lambda v: None  
        }
        exclude = {"selected_invs"}

    def set_default(self):
        """Resets all fields to their default values."""
        self.__fields_set__.clear()
        for field_name, field in self.__fields__.items():
            setattr(self, field_name, field.get_default())

    # TODO: check if it makes sense to use SeismoLocation instead of separate
    # props.
    # seismo_location: List[SeismoLocation] = None

    # FIXME: for now we just assume all values are 
    # given in one string separated with "," -> e.g.
    # channel = CH,HH,BH,EH

class EventConfig(BaseModel):
    client              : Optional   [str] = "IRIS"
    date_config         : DateConfig                 = DateConfig(
        start_time=datetime(2024, 8, 20),
        end_time=datetime(2024, 9, 20)
    )
    model               : str = 'iasp91'
    min_depth           : float = 0.0
    max_depth           : float = 6800.0
    min_magnitude       : float = 5.0
    max_magnitude       : float = 10.0
    min_radius          : float = 30.0
    max_radius          : float = 90.0
    before_p_sec        : int = 10
    after_p_sec         : int = 130
    include_all_origins : bool = False
    include_all_magnitudes: bool = False
    include_arrivals    : bool = False
    limit               : Optional[str] = None
    offset              : Optional[str] = None
    local_catalog       : Optional[str] = None
    contributor         : Optional[str] = None
    updated_after       : Optional[str] = None

    selected_catalogs   : Optional[Any] = None

    geo_constraint      : Optional[List[GeometryConstraint]] = None

    class Config:
        json_encoders = {
            Any: lambda v: None  
        }
        exclude = {"selected_catalogs"}

    def set_default(self):
        """Resets all fields to their default values."""
        self.__fields_set__.clear()
        for field_name, field in self.__fields__.items():
            setattr(self, field_name, field.get_default())      

class PredictionData(BaseModel):
    event_id: str
    station_id: str
    p_arrival: datetime
    s_arrival: datetime
class SeismoLoaderSettings(BaseModel):
    sds_path          : str                                   = None
    db_path           : str                                   = None
    download_type     : DownloadType                          = DownloadType.EVENT
    selected_workflow : WorkflowType                          = WorkflowType.EVENT_BASED
    proccess          : ProcessingConfig                      = None
    client_url_mapping: Optional[dict]                        = {}
    extra_clients     : Optional[dict]                        = {}
    auths             : Optional        [List[AuthConfig]]    = []
    waveform          : WaveformConfig                        = None
    station           : StationConfig                         = None
    event             : EventConfig                           = None
    predictions       : Dict            [str, PredictionData] = {}


    def load_url_mapping(self):
        from obspy.clients.fdsn.header import URL_MAPPINGS
        self.client_url_mapping = load_original_client()
        self.extra_clients = load_extra_client()
        self.client_url_mapping.update(self.extra_clients)
        URL_MAPPINGS.update(self.client_url_mapping)


    def set_download_type_from_workflow(self):
        if (
            self.selected_workflow == WorkflowType.EVENT_BASED or
            self.selected_workflow == WorkflowType.STATION_BASED
        ):
            self.download_type = DownloadType.EVENT

        if (self.selected_workflow == WorkflowType.CONTINUOUS):
            self.download_type = DownloadType.CONTINUOUS



    @classmethod
    def _check_val(cls, val, default_val, val_type: str = "int", return_empty_str: bool = False):
        if val is not None and not isinstance(val, str):
            return val
        
        if val is None or val.strip().lower() == 'none':
            return default_val
        
        # For cases where user purposedly is passing empty string
        if val.strip() == '':
            if return_empty_str:
                return ''
            return default_val

        else:            
            if val_type == "int":
                return int(val)
            if val_type == "float":
                return float(val)
            return val
        

    @classmethod
    def _is_none(cls, val):
        if val is None or isinstance(val, str): 
            if val.strip() == '' or val.strip().lower() == 'none':
                return True
        return False
            
    @classmethod
    def from_cfg_file(cls, cfg_source: Union[str, IO]) -> "SeismoLoaderSettings":
        config = configparser.ConfigParser()
        config.optionxform = str
        warnings: List[str] = []
        errors: List[str] = []  # Track errors

        # Load configuration file
        cls._load_config_file(cfg_source, config)

        # Parse sections
        sds_path = cls._parse_sds_section(config, warnings, errors)
        db_path = cls._parse_database_section(config, sds_path, warnings, errors)
        processing_config, download_type = cls._parse_processing_section(config, warnings, errors)
        lst_auths = cls._parse_auth_section(config, warnings, errors)
        waveform = cls._parse_waveform_section(config, warnings, errors)
        station_config = cls._parse_station_section(config, warnings, errors)
        event_config = cls._parse_event_section(config, warnings, errors)

        # Display warnings and errors
        if warnings:
            for warning in warnings:
                print(f"Warning: {warning}")
        if errors:
            for error in errors:
                print(f"Error: {error}")
            # raise ValueError("Errors encountered during configuration parsing. Please check the logs.")

        # Return the populated SeismoLoaderSettings
        return cls(
            sds_path=sds_path,
            db_path=db_path,
            download_type=download_type,
            proccess=processing_config,
            auths=lst_auths,
            waveform=waveform,
            station=station_config,
            event=event_config,
        )
    
    @classmethod
    def _load_config_file(cls, cfg_source, config):
        if isinstance(cfg_source, str):
            cfg_path = os.path.abspath(cfg_source)
            if not os.path.exists(cfg_path):
                raise ValueError(f"File not found in the following path: {cfg_path}")
            config.read(cfg_path)
        else:
            try:
                config.read_file(cfg_source)
            except Exception as e:
                raise ValueError(f"Failed to read configuration file: {str(e)}")

    @classmethod
    def _parse_sds_section(cls, config, warnings, errors):
        try:
            sds_path = config.get('SDS', 'sds_path', fallback=None)
            if not sds_path:
                sds_path = "data/SDS"
                warnings.append("Warning: 'sds_path' is missing in the [SDS] section. Using default value: 'data/SDS'.")
            return sds_path
        except Exception as e:
            errors.append(f"Error parsing [SDS] section: {str(e)}")
            return None            

    @classmethod
    def _parse_database_section(cls, config, sds_path, warnings, errors):
        try:
            db_path = config.get('DATABASE', 'db_path', fallback=None).strip()
            if not db_path:
                db_path = f'{sds_path}/database.sqlite'
                warnings.append(f"Warning: 'db_path' is missing or empty in the [DATABASE] section. Using default value: '{db_path}'.")
            return db_path
        except Exception as e:
            errors.append(f"Error parsing [DATABASE] section: {str(e)}")
            return None
                    
    @classmethod
    def _parse_processing_section(cls, config, warnings, errors):
        # Parse num_processes
        num_processes = config.get('PROCESSING', 'num_processes', fallback=None)
        try:
            num_processes = cls._check_val(num_processes, 2, "int")
        except ValueError:
            num_processes = 2  # Default value
            warnings.append("Warning: 'num_processes' is missing or invalid in the [PROCESSING] section. Using default value: '2'.")

        # Parse gap_tolerance
        gap_tolerance = config.get('PROCESSING', 'gap_tolerance', fallback=None)
        try:
            gap_tolerance = cls._check_val(gap_tolerance, 60, "int")
        except ValueError:
            gap_tolerance = 60  # Default value
            warnings.append("Warning: 'gap_tolerance' is missing or invalid in the [PROCESSING] section. Using default value: '60'.")

        # Parse and validate download_type
        download_type_str = config.get('PROCESSING', 'download_type', fallback='').strip().lower()
        if download_type_str not in DownloadType._value2member_map_:
            warnings.append(f"Warning: Invalid download_type '{download_type_str}' found in config. Defaulting to 'event'.")
            download_type_str = DownloadType.EVENT.value  # Default to 'event'
        download_type = DownloadType(download_type_str)

        # Return the ProcessingConfig object
        return ProcessingConfig(
            num_processes=num_processes,
            gap_tolerance=gap_tolerance,
        ), download_type


    @classmethod
    def _parse_auth_section(cls, config, warnings, errors):
        try:
            credentials = list(config['AUTH'].items())
            return [
                AuthConfig(nslc_code=nslc, username=cred.split(':')[0], password=cred.split(':')[1])
                for nslc, cred in credentials
            ]
        except Exception as e:
            errors.append(f"Error parsing [AUTH] section: {str(e)}")
            return []
        

    @classmethod
    def _parse_waveform_section(cls, config, warnings, errors):
        waveform_section = 'WAVEFORM'
        if not config.has_section(waveform_section):
            errors.append(f"Error: The [{waveform_section}] section is missing in the configuration file.")

        client = config.get(waveform_section, 'client', fallback=None)
        if client is None or not client.strip():
            client = "EARTHSCOPE"
            warnings.append(f"Warning: 'client' is missing or empty in the [{waveform_section}] section. Defaulting to 'EARTHSCOPE'.")

        days_per_request = config.get(waveform_section, 'days_per_request', fallback=None)
        if days_per_request is None:
            errors.append(f"Error: 'days_per_request' is missing in the [{waveform_section}] section.")
        days_per_request = cls._check_val(days_per_request, 1, "int")

        channel_pref = config.get(waveform_section, 'channel_pref', fallback='').strip()
        location_pref = config.get(waveform_section, 'location_pref', fallback='').strip()

        return WaveformConfig(
            client=client,
            channel_pref=channel_pref,
            location_pref=location_pref,
            days_per_request=days_per_request,
        )
            
    @classmethod
    def _parse_station_section(cls, config, warnings, errors):
        station_section = 'STATION'
        if not config.has_section(station_section):
            errors.append(f"Error: The [{station_section}] section is missing in the configuration file. Please provide station details.")
        
        station_client = cls._parse_param(
            config=config,
            section=station_section,
            key='client',
            default="EARTHSCOPE",
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'client' is missing in the [{station_section}] section. Specify the client for station data retrieval.",
            warning_message=f"Warning: 'client' is empty in the [{station_section}] section. Defaulting to 'EARTHSCOPE'.",
            validation_fn=lambda x: bool(x.strip())  # Ensure the value is not empty after stripping
        )

        network = cls._parse_param(
            config=config,
            section=station_section,
            key='network',
            default="GSN",
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'network' is missing in the [{station_section}] section. Please specify a network.",
            warning_message=f"Warning: 'network' is empty in the [{station_section}] section. Defaulting to 'GSN'."
        )

        station = cls._parse_param(
            config=config,
            section=station_section,
            key='station',
            default="",
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'station' is missing in the [{station_section}] section. Please specify a station.",
            warning_message=f"Warning: 'station' is empty in the [{station_section}] section. Defaulting to an empty string."
        )

        location = cls._parse_param(
            config=config,
            section=station_section,
            key='location',
            default="*",
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'location' is missing in the [{station_section}] section. Please specify a location.",
            warning_message=f"Warning: 'location' is empty in the [{station_section}] section. Defaulting to '*'."
        )

        channel = cls._parse_param(
            config=config,
            section=station_section,
            key='channel',
            default="?H?,?N?",
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'channel' is missing in the [{station_section}] section. Please specify a channel.",
            warning_message=f"Warning: 'channel' is empty in the [{station_section}] section. Defaulting to '?H?,?N?'.",
            validation_fn=lambda x: bool(re.match(r'^(\?[\w]\?,?)+$', x))
        )
        
        geo_constraint_station = cls._parse_geo_constraint(config, 'STATION', warnings, errors)

        # Parse force_stations
        force_stations_cmb_n_s = config.get(station_section, 'force_stations', fallback='').split(',')
        force_stations = [SeismoQuery(cmb_str_n_s=cmb_n_s) for cmb_n_s in force_stations_cmb_n_s if cmb_n_s.strip()]

        # Parse exclude_stations
        exclude_stations_cmb_n_s = config.get(station_section, 'exclude_stations', fallback='').split(',')
        exclude_stations = [SeismoQuery(cmb_str_n_s=cmb_n_s) for cmb_n_s in exclude_stations_cmb_n_s if cmb_n_s.strip()]

        # Parse local_inventory
        local_inventory = config.get(station_section, 'local_inventory', fallback=None)

 

        # Parse include_restricted
        include_restricted = cls._check_val(
            config.get(station_section, 'include_restricted', fallback='False'), False, "bool"
        )

        # Parse level
        level = config.get(station_section, 'level', fallback=None)
        if level is None:  # Key is missing
            errors.append(f"Error: 'level' is missing in the [{station_section}] section. Please specify a level (e.g., 'channel').")
        else:
            level = level.strip()
            if not level:  # Value is empty
                level= Levels.CHANNEL
                warnings.append(f"Warning: 'level' is empty in the [{station_section}] section. Defaulting to 'channel'.")

        # Parse date configurations
        date_config = DateConfig(
            start_time=parse_time(config.get(station_section, 'starttime', fallback=None)),
            end_time=parse_time(config.get(station_section, 'endtime', fallback=None)),
            start_before=parse_time(config.get(station_section, 'startbefore', fallback=None)),
            start_after=parse_time(config.get(station_section, 'startafter', fallback=None)),
            end_before=parse_time(config.get(station_section, 'endbefore', fallback=None)),
            end_after=parse_time(config.get(station_section, 'endafter', fallback=None)),
        )

        # Build the StationConfig object
        return StationConfig(
            client=station_client,
            local_inventory=local_inventory,
            force_stations=force_stations,
            exclude_stations=exclude_stations,
            date_config=date_config,
            network=network,
            station=station,
            location=location,
            channel=channel,
            geo_constraint=[geo_constraint_station] if geo_constraint_station else [],
            include_restricted=include_restricted,
            level=level,
        )

    @classmethod
    def _parse_event_section(cls, config, warnings, errors):
        """
        Parse and validate the EVENT section of the configuration file.

        Args:
            config: ConfigParser object.
            warnings: List to append warnings.
            errors: List to append errors.

        Returns:
            EventConfig object.
        """
        event_section = "EVENT"

        # Ensure the EVENT section exists
        if not config.has_section(event_section):
            errors.append(f"Error: The [{event_section}] section is missing in the configuration file.")
            return None

        # Parse required parameters
        event_client = cls._parse_param(
            config=config,
            section=event_section,
            key="client",
            default="EARTHSCOPE",
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'client' is missing in the [{event_section}] section. Specify a client.",
            warning_message=f"Warning: 'client' is empty in the [{event_section}] section. Defaulting to 'EARTHSCOPE'.",
            validation_fn=lambda x: bool(x.strip())
        )

        model = cls._parse_param(
            config=config,
            section=event_section,
            key="model",
            default="iasp91",
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'model' is missing in the [{event_section}] section. Specify a model.",
            warning_message=f"Warning: 'model' is empty in the [{event_section}] section. Defaulting to 'iasp91'."
        )

        start_time = cls._parse_param(
            config=config,
            section=event_section,
            key="starttime",
            default=(datetime.now() - timedelta(days=30)).isoformat(),
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'starttime' is missing in the [{event_section}] section. Specify a valid start time.",
            warning_message=f"Warning: 'starttime' is empty in the [{event_section}] section. Defaulting to 1 month before the current time.",
            validation_fn=lambda x: parse_time(x) is not None
        )
        start_time = parse_time(start_time)

        end_time = cls._parse_param(
            config=config,
            section=event_section,
            key="endtime",
            default=datetime.now().isoformat(),
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'endtime' is missing in the [{event_section}] section. Specify a valid end time.",
            warning_message=f"Warning: 'endtime' is empty in the [{event_section}] section. Defaulting to the current time.",
            validation_fn=lambda x: parse_time(x) is not None
        )
        end_time = parse_time(end_time)

        before_p_sec = cls._parse_param(
            config=config,
            section=event_section,
            key="before_p_sec",
            default=20,
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'before_p_sec' is missing in the [{event_section}] section. Specify a valid integer.",
            warning_message=f"Warning: 'before_p_sec' is empty in the [{event_section}] section. Defaulting to '20'.",
            validation_fn=lambda x: x.isdigit()
        )
        before_p_sec = int(before_p_sec)

        after_p_sec = cls._parse_param(
            config=config,
            section=event_section,
            key="after_p_sec",
            default=130,
            warnings=warnings,
            errors=errors,
            error_message=f"Error: 'after_p_sec' is missing in the [{event_section}] section. Specify a valid integer.",
            warning_message=f"Warning: 'after_p_sec' is empty in the [{event_section}] section. Defaulting to '130'.",
            validation_fn=lambda x: x.isdigit()
        )
        after_p_sec = int(after_p_sec)

        # Parse optional numerical parameters
        min_depth = cls._check_val(config.get(event_section, "min_depth", fallback=-3), -3, "float")
        max_depth = cls._check_val(config.get(event_section, "max_depth", fallback=600), 600, "float")
        min_magnitude = cls._check_val(config.get(event_section, "minmagnitude", fallback=5.5), 5.5, "float")
        max_magnitude = cls._check_val(config.get(event_section, "maxmagnitude", fallback=7.7), 7.7, "float")
        min_radius = cls._check_val(config.get(event_section, "minradius", fallback=30.0), 30.0, "float")
        max_radius = cls._check_val(config.get(event_section, "maxradius", fallback=90.0), 90.0, "float")

        if min_radius < 0 or max_radius < 0:
            errors.append(f"Error: 'min_radius' and 'max_radius' must be positive values in the [{event_section}] section.")
        if min_radius >= max_radius:
            errors.append(f"Error: 'min_radius' must be less than 'max_radius' in the [{event_section}] section.")

        # Parse boolean flags
        include_all_origins = cls._check_val(config.get(event_section, "includeallorigins", fallback=False), False, "bool")
        include_all_magnitudes = cls._check_val(config.get(event_section, "includeallmagnitudes", fallback=False), False, "bool")
        include_arrivals = cls._check_val(config.get(event_section, "includearrivals", fallback=False), False, "bool")

        # Parse optional strings
        limit = config.get(event_section, "limit", fallback=None)
        offset = config.get(event_section, "offset", fallback=None)
        local_catalog = config.get(event_section, "local_catalog", fallback=None)
        contributor = config.get(event_section, "contributor", fallback=None)
        updated_after = config.get(event_section, "updated_after", fallback=None)

        # Parse geo_constraint
        geo_constraint_event = cls._parse_geo_constraint(config, event_section, warnings, errors)

        # Return EventConfig object
        return EventConfig(
            client=event_client,
            model=model,
            date_config=DateConfig(start_time=start_time, end_time=end_time),
            min_depth=min_depth,
            max_depth=max_depth,
            min_magnitude=min_magnitude,
            max_magnitude=max_magnitude,
            min_radius=min_radius,
            max_radius=max_radius,
            before_p_sec=before_p_sec,
            after_p_sec=after_p_sec,
            geo_constraint=[geo_constraint_event] if geo_constraint_event else [],
            include_all_origins=include_all_origins,
            include_all_magnitudes=include_all_magnitudes,
            include_arrivals=include_arrivals,
            limit=limit,
            offset=offset,
            local_catalog=local_catalog,
            contributor=contributor,
            updated_after=updated_after,
        )



    @staticmethod
    def _parse_param(
        config,
        section,
        key,
        default=None,
        validation_fn=None,
        warnings=None,
        errors=None,
        error_message=None,
        warning_message=None,
    ):
        """
        Parse and validate a parameter from the configuration.

        Args:
            config: ConfigParser object.
            section: Section name (e.g., 'STATION' or 'EVENT').
            key: Parameter key to parse.
            default: Default value to use if the parameter is missing or invalid.
            validation_fn: Optional function to validate the parameter's value.
            warnings: List to append warnings.
            errors: List to append errors.
            error_message: Custom error message for missing parameters.
            warning_message: Custom warning message for empty parameters.

        Returns:
            The parsed and validated parameter value.
        """
        try:
            value = config.get(section, key, fallback=None)
            if value is None:  # Key is missing
                if error_message and errors is not None:
                    errors.append(error_message)
                return default
            value = value.strip()
            if not value:  # Value is empty
                if warning_message and warnings is not None:
                    warnings.append(warning_message)
                return default
            if validation_fn and not validation_fn(value):
                if error_message and errors is not None:
                    errors.append(error_message)
                return default
            return value
        except Exception as e:
            if errors is not None:
                errors.append(f"Error parsing '{key}' in the [{section}] section: {str(e)}")
            return default

    @staticmethod
    def _parse_geo_constraint(config, section, warnings, errors):
        """
        Parse and validate the geo_constraint for a given section.

        Args:
            config: ConfigParser object.
            section: Section name (e.g., 'STATION' or 'EVENT').
            warnings: List to append warnings.
            errors: List to append errors.

        Returns:
            A GeometryConstraint object if valid geo_constraint is found; otherwise, an empty list.
        """
        geo_constraint_type = config.get(section, 'geo_constraint', fallback=None)
        geo_constraint = []

        if geo_constraint_type == GeoConstraintType.BOUNDING:
            # Parse bounding box coordinates
            min_lat = cls._check_val(config.get(section, 'minlatitude'), None, "float")
            max_lat = cls._check_val(config.get(section, 'maxlatitude'), None, "float")
            min_lng = cls._check_val(config.get(section, 'minlongitude'), None, "float")
            max_lng = cls._check_val(config.get(section, 'maxlongitude'), None, "float")

            # Validate longitude range and adjust if necessary
            if max_lng is not None and max_lng > 180:
                max_lng -= 360
                warnings.append(f"Warning: 'maxlongitude' exceeded 180 in the [{section}] section. Adjusted to {max_lng}.")
            if min_lng is not None and min_lng < -180:
                min_lng += 360
                warnings.append(f"Warning: 'minlongitude' was below -180 in the [{section}] section. Adjusted to {min_lng}.")

            # Create bounding box constraint
            geo_constraint = GeometryConstraint(
                coords=RectangleArea(
                    min_lat=min_lat,
                    max_lat=max_lat,
                    min_lng=min_lng,
                    max_lng=max_lng,
                )
            )

        elif geo_constraint_type == GeoConstraintType.CIRCLE:
            # Parse circle area coordinates
            lat = cls._check_val(config.get(section, 'latitude'), None, "float")
            lng = cls._check_val(config.get(section, 'longitude'), None, "float")
            min_radius = cls._check_val(config.get(section, 'minsearchradius'), None, "float")
            max_radius = cls._check_val(config.get(section, 'maxsearchradius'), None, "float")

            # Validate longitude range and adjust if necessary
            if lng is not None and lng > 180:
                lng -= 360
                warnings.append(f"Warning: 'longitude' exceeded 180 in the [{section}] section. Adjusted to {lng}.")
            if lng is not None and lng < -180:
                lng += 360
                warnings.append(f"Warning: 'longitude' was below -180 in the [{section}] section. Adjusted to {lng}.")

            # Create circular area constraint
            geo_constraint = GeometryConstraint(
                coords=CircleArea(
                    lat=lat,
                    lng=lng,
                    min_radius=min_radius,
                    max_radius=max_radius,
                )
            )

        elif geo_constraint_type is not None:  # Invalid type provided
            # Log error for invalid geo_constraint types
            errors.append(
                f"Error: Invalid 'geo_constraint' type '{geo_constraint_type}' in the [{section}] section. "
                f"Allowed values are 'BOUNDING' or 'CIRCLE'."
            )

        return geo_constraint


    def to_cfg(self) -> ConfigParser:
        config = ConfigParser()

        # Populate the [SDS] section
        config['SDS'] = {}
        safe_add_to_config(config, 'SDS', 'sds_path', self.sds_path)

        # Populate the [DATABASE] section
        config['DATABASE'] = {}
        safe_add_to_config(config, 'DATABASE', 'db_path', self.db_path)

        # Populate the [PROCESSING] section
        config['PROCESSING'] = {}
        safe_add_to_config(config, 'PROCESSING', 'num_processes', self.proccess.num_processes)
        safe_add_to_config(config, 'PROCESSING', 'gap_tolerance', self.proccess.gap_tolerance)
        safe_add_to_config(config, 'PROCESSING', 'download_type', self.download_type.value)

        # Populate the [AUTH] section
        config['AUTH'] = {}
        if self.auths:
            for auth in self.auths:
                safe_add_to_config(config, 'AUTH', auth.nslc_code, f"{auth.username}:{auth.password}")


        # Populate the [WAVEFORM] section
        config['WAVEFORM'] = {}
        safe_add_to_config(config, 'WAVEFORM', 'client', self.waveform.client)
        safe_add_to_config(config, 'WAVEFORM', 'channel_pref', self.waveform.channel_pref)
        safe_add_to_config(config, 'WAVEFORM', 'location_pref', self.waveform.location_pref)
        safe_add_to_config(config, 'WAVEFORM', 'days_per_request', self.waveform.days_per_request)

        # Populate the [STATION] section
        if self.station:
            config['STATION'] = {}
            safe_add_to_config(config, 'STATION', 'client', self.station.client)
            safe_add_to_config(config, 'STATION', 'local_inventory', self.station.local_inventory)
            safe_add_to_config(config, 'STATION', 'force_stations', ','.join([convert_to_str(station.cmb_str) for station in self.station.force_stations if station.cmb_str is not None]))
            safe_add_to_config(config, 'STATION', 'exclude_stations', ','.join([convert_to_str(station.cmb_str) for station in self.station.exclude_stations if station.cmb_str is not None]))
            safe_add_to_config(config, 'STATION', 'starttime', self.station.date_config.start_time)
            safe_add_to_config(config, 'STATION', 'endtime', self.station.date_config.end_time)
            safe_add_to_config(config, 'STATION', 'network', self.station.network)
            safe_add_to_config(config, 'STATION', 'station', self.station.station)
            safe_add_to_config(config, 'STATION', 'location', self.station.location)
            safe_add_to_config(config, 'STATION', 'channel', self.station.channel)
            safe_add_to_config(config, 'STATION', 'station', self.station.station)
            safe_add_to_config(config, 'STATION', 'location', self.station.location)  # Ensure location is added
            safe_add_to_config(config, 'STATION', 'channel', self.station.channel)    # Ensure channel is added


            # FIXME: The settings are updated such that they support multiple geometries.
            # But config file only accepts one geometry at a time. For now we just get
            # the first item.
            if self.station.geo_constraint and hasattr(self.station.geo_constraint[0], 'geo_type'):
                safe_add_to_config(config, 'STATION', 'geo_constraint', self.station.geo_constraint[0].geo_type)
                
                if self.station.geo_constraint[0].geo_type == GeoConstraintType.CIRCLE:
                    safe_add_to_config(config, 'STATION', 'latitude', self.station.geo_constraint[0].coords.lat)
                    safe_add_to_config(config, 'STATION', 'longitude', self.station.geo_constraint[0].coords.lng)
                    safe_add_to_config(config, 'STATION', 'minradius', self.station.geo_constraint[0].coords.min_radius)
                    safe_add_to_config(config, 'STATION', 'maxradius', self.station.geo_constraint[0].coords.max_radius)

                if self.station.geo_constraint[0].geo_type == GeoConstraintType.BOUNDING:
                    safe_add_to_config(config, 'STATION', 'minlatitude', self.station.geo_constraint[0].coords.min_lat)
                    safe_add_to_config(config, 'STATION', 'maxlatitude', self.station.geo_constraint[0].coords.max_lat)
                    safe_add_to_config(config, 'STATION', 'minlongitude', self.station.geo_constraint[0].coords.min_lng)
                    safe_add_to_config(config, 'STATION', 'maxlongitude', self.station.geo_constraint[0].coords.max_lng)

            safe_add_to_config(config, 'STATION', 'includerestricted', self.station.include_restricted)
            safe_add_to_config(config, 'STATION', 'level', self.station.level.value)

        # Check if the main section is EventConfig or StationConfig and populate accordingly
        if self.event:
            config['EVENT'] = {}
            safe_add_to_config(config, 'EVENT', 'client', self.event.client)
            safe_add_to_config(config, 'EVENT', 'min_depth', self.event.min_depth)
            safe_add_to_config(config, 'EVENT', 'max_depth', self.event.max_depth)
            safe_add_to_config(config, 'EVENT', 'minmagnitude', self.event.min_magnitude)
            safe_add_to_config(config, 'EVENT', 'maxmagnitude', self.event.max_magnitude)
            safe_add_to_config(config, 'EVENT', 'minradius', self.event.min_radius)
            safe_add_to_config(config, 'EVENT', 'maxradius', self.event.max_radius)
            safe_add_to_config(config, 'EVENT', 'after_p_sec', self.event.after_p_sec)
            safe_add_to_config(config, 'EVENT', 'before_p_sec', self.event.before_p_sec)
            safe_add_to_config(config, 'EVENT', 'includeallorigins', self.event.include_all_origins)
            safe_add_to_config(config, 'EVENT', 'includeallmagnitudes', self.event.include_all_magnitudes)
            safe_add_to_config(config, 'EVENT', 'includearrivals', self.event.include_arrivals)
            safe_add_to_config(config, 'EVENT', 'limit', self.event.limit)
            safe_add_to_config(config, 'EVENT', 'offset', self.event.offset)
            safe_add_to_config(config, 'EVENT', 'local_catalog', self.event.local_catalog)
            safe_add_to_config(config, 'EVENT', 'contributor', self.event.contributor)
            safe_add_to_config(config, 'EVENT', 'updatedafter', self.event.updated_after)

            # FIXME: The settings are updated such that they support multiple geometries.
            # But config file only accepts one geometry at a time.For now we just get
            # the first item.
         
            if self.event.geo_constraint and hasattr(self.event.geo_constraint[0], 'geo_type'):
                safe_add_to_config(config, 'EVENT', 'geo_constraint', self.event.geo_constraint[0].geo_type)

                if self.event.geo_constraint[0].geo_type == GeoConstraintType.CIRCLE:
                    safe_add_to_config(config, 'EVENT', 'latitude', self.event.geo_constraint[0].coords.lat)
                    safe_add_to_config(config, 'EVENT', 'longitude', self.event.geo_constraint[0].coords.lng)
                    safe_add_to_config(config, 'EVENT', 'minsearchradius', self.event.geo_constraint[0].coords.min_radius)
                    safe_add_to_config(config, 'EVENT', 'maxsearchradius', self.event.geo_constraint[0].coords.max_radius)

                if self.event.geo_constraint[0].geo_type == GeoConstraintType.BOUNDING:
                    safe_add_to_config(config, 'EVENT', 'minlatitude', self.event.geo_constraint[0].coords.min_lat)
                    safe_add_to_config(config, 'EVENT', 'maxlatitude', self.event.geo_constraint[0].coords.max_lat)
                    safe_add_to_config(config, 'EVENT', 'minlongitude', self.event.geo_constraint[0].coords.min_lng)
                    safe_add_to_config(config, 'EVENT', 'maxlongitude', self.event.geo_constraint[0].coords.max_lng)

        return config

    def add_to_config(self):
        config_dict = {
            'sds_path': self.sds_path,
            'db_path': self.db_path,
            'proccess': {
                'num_processes': self.proccess.num_processes,
                'gap_tolerance': self.proccess.gap_tolerance,
            },            
            'download_type': self.download_type.value if self.download_type else None,
            'auths': self.auths if self.auths else [],
            'waveform': {
                'client': self.waveform.client if self.waveform and self.waveform.client else None,
                'channel_pref': self.waveform.channel_pref if self.waveform else None,
                'location_pref': self.waveform.location_pref if self.waveform else None,
                'days_per_request': self.waveform.days_per_request if self.waveform and self.waveform.days_per_request is not None else None,
            },
            'station': {
                'client': self.station.client if self.station and self.station.client else None,
                'local_inventory': self.station.local_inventory if self.station else None,
                'force_stations': [station.cmb_str for station in self.station.force_stations if station.cmb_str is not None] if self.station and isinstance(self.station.force_stations, list) else [],
                'exclude_stations': [station.cmb_str for station in self.station.exclude_stations if station.cmb_str is not None] if self.station and isinstance(self.station.exclude_stations, list) else [],
                'starttime': self.station.date_config.start_time if self.station and self.station.date_config else None,
                'endtime': self.station.date_config.end_time if self.station and self.station.date_config else None,
                'startbefore': self.station.date_config.start_before if self.station and self.station.date_config else None,
                'startafter': self.station.date_config.start_after if self.station and self.station.date_config else None,
                'endbefore': self.station.date_config.end_before if self.station and self.station.date_config else None,
                'endafter': self.station.date_config.end_after if self.station and self.station.date_config else None,
                'network': self.station.network if self.station else None,
                'station': self.station.station if self.station else None,
                'location': self.station.location if self.station else None,
                'channel': self.station.channel if self.station else None,
                'geo_constraint': self.station.geo_constraint if self.station else None,
                'includerestricted': self.station.include_restricted if self.station else None,
                'level': self.station.level.value if self.station and self.station.level else None,
            },
            'event': {
                'client': self.event.client if self.event and self.event.client else None,
                'model': self.event.model if self.event and self.event.model else None,
                'before_p_sec': self.event.before_p_sec if self.event and self.event.before_p_sec is not None else None,
                'after_p_sec': self.event.after_p_sec if self.event and self.event.after_p_sec is not None else None,
                'starttime': self.event.date_config.start_time if self.event and self.event.date_config else None,
                'endtime': self.event.date_config.end_time if self.event and self.event.date_config else None,
                'min_depth': self.event.min_depth if self.event and self.event.min_depth is not None else None,
                'max_depth': self.event.max_depth if self.event and self.event.max_depth is not None else None,
                'minmagnitude': self.event.min_magnitude if self.event and self.event.min_magnitude is not None else None,
                'maxmagnitude': self.event.max_magnitude if self.event and self.event.max_magnitude is not None else None,
                'minradius': self.event.min_radius if self.event and self.event.min_radius is not None else None,
                'maxradius': self.event.max_radius if self.event and self.event.max_radius is not None else None,
                'local_catalog': self.event.local_catalog if self.event else None,
                'geo_constraint': self.event.geo_constraint if self.event else None,
                'includeallorigins': self.event.include_all_origins if self.event else None,
                'includeallmagnitudes': self.event.include_all_magnitudes if self.event else None,
                'includearrivals': self.event.include_arrivals if self.event else None,
                'limit': self.event.limit if self.event and self.event.limit is not None else None,
                'offset': self.event.offset if self.event and self.event.offset is not None else None,
                'contributor': self.event.contributor if self.event else None,
                'updatedafter': self.event.updated_after if self.event else None,
            }
        }
        return config_dict


    def add_prediction(self, event_id: str, station_id: str, p_arrival: datetime, s_arrival: datetime):
        key = f"{event_id}|{station_id}"
        self.predictions[key] = PredictionData(
            event_id=event_id,
            station_id=station_id,
            p_arrival=p_arrival,
            s_arrival=s_arrival
        )

    def get_prediction(self, event_id: str, station_id: str) -> Optional[PredictionData]:
        key = f"{event_id}|{station_id}"
        return self.predictions.get(key)
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_pickle(self, pickle_path: str) -> None:
        """Serialize the SeismoLoaderSettings instance to a pickle file."""
        with open(pickle_path, "wb") as f:
            pickle.dump(self, f)
    
    @classmethod
    def from_pickle_file(cls, pickle_path: str) -> "SeismoLoaderSettings":
        """Load a SeismoLoaderSettings instance from a pickle file."""
        with open(pickle_path, "rb") as f:
            return pickle.load(f)        