from enum import Enum


class DownloadType(str, Enum):
    EVENT  = 'event'
    CONTIN = 'continuous'


class SeismoClients(str, Enum):
    AUSPASS    = "AUSPASS"      # http://auspass.edu.au
    BGR        = "BGR"          # http://eida.bgr.de
    EIDA       = "EIDA"         # http://eida-federator.ethz.ch
    EMSC       = "EMSC"         # http://www.seismicportal.eu
    ETH        = "ETH"          # http://eida.ethz.ch
    GEOFON     = "GEOFON"       # http://geofon.gfz-potsdam.de
    GEONET     = "GEONET"       # http://service.geonet.org.nz
    GFZ        = "GFZ"          # http://geofon.gfz-potsdam.de
    ICGC       = "ICGC"         # http://ws.icgc.cat
    IESDMC     = "IESDMC"       # http://batsws.earth.sinica.edu.tw
    INGV       = "INGV"         # http://webservices.ingv.it
    IPGP       = "IPGP"         # http://ws.ipgp.fr
    IRIS       = "IRIS"         # http://service.iris.edu
    IRISPH5    = "IRISPH5"      # http://service.iris.edu
    ISC        = "ISC"          # http://www.isc.ac.uk
    KNMI       = "KNMI"         # http://rdsa.knmi.nl
    KOERI      = "KOERI"        # http://eida.koeri.boun.edu.tr
    LMU        = "LMU"          # https://erde.geophysik.uni-muenchen.de
    NCEDC      = "NCEDC"        # http://service.ncedc.org
    NIEP       = "NIEP"         # http://eida-sc3.infp.ro
    NOA        = "NOA"          # http://eida.gein.noa.gr
    ODC        = "ODC"          # http://www.orfeus-eu.org
    ORFEUS     = "ORFEUS"       # http://www.orfeus-eu.org
    RASPISHAKE = "RASPISHAKE"   # https://data.raspberryshake.org
    RESIF      = "RESIF"        # http://ws.resif.fr
    RESIFPH5   = "RESIFPH5"     # http://ph5ws.resif.fr
    SCEDC      = "SCEDC"        # http://service.scedc.caltech.edu
    TEXNET     = "TEXNET"       # http://rtserve.beg.utexas.edu
    UIB_NORSAR = "UIB-NORSAR"   # http://eida.geo.uib.no
    USGS       = "USGS"         # http://earthquake.usgs.gov
    USP        = "USP"          # http://sismo.iag.usp.br
    EARTHSCOPE = 'EARTHSCOPE'   # FIXME: UNKNOWN


class GeoConstraintType(str, Enum):
    BOUNDING = 'bounding'
    CIRCLE   = 'circle'
    NONE     = 'neither'


class Levels(str, Enum):
    CHANNEL = 'channel'


class EventModels(str, Enum):
    IASP91 = 'iasp91'