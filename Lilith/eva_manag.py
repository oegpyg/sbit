__doc__ = """
Modulo de tools de formateado de estructura de datos
"""
import re
from django.conf import settings
from django.shortcuts import resolve_url
import json
from decimal import Decimal
import uuid
import base64
from django.db.models.fields.files import ImageFieldFile
import datetime
from django.utils.timezone import is_aware

class EvaQuery(object):
    def __init__(self, *args, **kwargs):
        pass

    def querydict_params(self, *args, **kwargs):
        exclude = kwargs.get('exclude')
        querylist = kwargs.get('querylist')
        lexc = ['columns',
                     'start',
                     'draw',
                     'length',
                     'search',
                    'order',
                    r'\b-\b',
                     'filtro',
                     r'\b_\b',
                     'from_palletl',
                     'interface',
                     'demo',
                     'key_name',
                     'app_name',
                     'model_name',
                     'model_key',
                     'api_key',
                     'method_call',
                     '^nor_',
                     '^or_',
                    'distinct_value',
                    'class_name',
                    'method_name',
                    'app_name',
                    'module_name',
                    'serial_model',
                    'type_datatable',
                    'init',
                    'last',
                    'pq_datatype',
                    'pq_rpp',
                    'dparamquery',
                    'pq_curpage',
                    'pq_filter',
                    'pq_sort',
                    'lookup',
                    'callback',
                    'jsonp',
                    'explicit_key',
                    'order_field',
                    'type_datatable',
                    'init',
                    'last',
                    'pq_datatype',
                    'pq_rpp',
                    'dparamquery',
                    'pq_curpage',
                    'pq_filter',
                    'pq_sort',
                    'lookup'
        ]
        lexc.extend(exclude)
        params = {}
        lexc = map(str, lexc)
        rsearch = '|'.join(lexc)
        for l in querylist:
            key = l[0]
            print key, l[1]
            if re.search(rsearch, key):
                continue
            if isinstance(key, str):
                if key.strip() == '':
                    continue
            key = key.replace('[]', '')
            if not l[1]:
                continue
            if len(l[1]) > 1:
                params.update({'%s__in' % key: l[1] })
            else:
                if isinstance(l[1][0], bool):
                    params.update({key:  l[1][0] })
                    continue
                if isinstance(l[1][0], str) or isinstance(l[1][0], unicode):
                    if len(l[1][0].split('|')) > 1:
                        params.update({'%s__in' % key: l[1][0].split('|') })
                        continue
                    if l[1][0].strip() == '':
                        continue
                    if l[1][0].strip() == 'on':
                        params.update({key: True })
                        continue
                try:
                    params.update({key: int(l[1][0].strip())})
                except:
                    params.update({key: l[1][0].strip()})
        return params

class EvaFormat(object):
    def __init__(self, *args, **kwargs):
        return

    def url_viewfull(viewname, **kwargs):
        if kwargs.get('filename'):
            urlfull = '%s%s' % (settings.GDOMAIN, resolve_url(viewname, kwargs.get('filename') ))
        else:
            urlfull = '%s%s' % (settings.GDOMAIN, resolve_url(viewname))
        return urlfull

    def suppress_score(self, *args, **kwargs):
        """Suprime espacios en blanco hasta encontrar un patron"""
        spaces = ' ' * (len(args[0].group()) -1)
        return '%s+' % spaces

    def mprinters_cods(self, *args, **kwargs):
        matrixc = {
                'CTL_LF':  '\x0a',              ## Feed control sequences Print and line feed
                'CTL_FF':  '\x0c',              # Form feed
                'CTL_CR':  '\x0d',              # Carriage return
                'CTL_HT':  '\x09',              # Horizontal tab
                'CTL_SET_HT':  '\x1b\x44',          # Set horizontal tab positions
                'CTL_VT':  '\x1b\x64\x04',      # Vertical tab
                'HW_INIT':  '\x1b\x40',          ## Printer hardware Clear data in buffer and reset modes
                'HW_SELECT':  '\x1b\x3d\x01',      # Printer select
                'HW_RESET':  '\x1b\x3f\x0a\x00',  # Reset printer hardware
                'CD_KICK_2':  '\x1b\x70\x00',      ## Cash Drawer Sends a pulse to pin 2 []
                'CD_KICK_5':  '\x1b\x70\x01',      # Sends a pulse to pin 5 []
                'PAPER_FULL_CUT':  '\x1d\x56\x00',## Paper Full cut paper
                'PAPER_PART_CUT':  '\x1d\x56\x01',# Partial cut paper
                'TXT_NORMAL':  '\x1b\x21\x00',## Text format Normal text
                'TXT_2HEIGHT':  '\x1b\x21\x10',# Double height text
                'TXT_2WIDTH':  '\x1b\x21\x20',# Double width text
                'TXT_4SQUARE':  '\x1b\x21\x30',# Quad area text
                'TXT_UNDERL_OFF':  '\x1b\x2d\x00',# Underline font OFF
                'TXT_UNDERL_ON':  '\x1b\x2d\x01',# Underline font 1-dot ON
                'TXT_UNDERL2_ON':  '\x1b\x2d\x02',# Underline font 2-dot ON
                'TXT_BOLD_OFF':  '\x1b\x45\x00',# Bold font OFF
                'TXT_BOLD_ON':  '\x1b\x45\x01',# Bold font ON
                'TXT_FONT_A':  '\x1b\x4d\x00',# Font type A
                'TXT_FONT_B':  '\x1b\x4d\x01', # Font type B
                'TXT_ALIGN_LT':  '\x1b\x61\x00', # Left justification
                'TXT_ALIGN_CT':  '\x1b\x61\x01', # Centering
                'TXT_ALIGN_RT':  '\x1b\x61\x02', # Right justification
                'CHARCODE_PC437':  '\x1b\x74\x00', ## Char code table USA: Standard Europe
                'CHARCODE_JIS':  '\x1b\x74\x01', # Japanese Katakana
                'CHARCODE_PC850':  '\x1b\x74\x02', # Multilingual
                'CHARCODE_PC860':  '\x1b\x74\x03', # Portuguese
                'CHARCODE_PC863':  '\x1b\x74\x04', # Canadian-French
                'CHARCODE_PC865':  '\x1b\x74\x05', # Nordic
                'CHARCODE_WEU':  '\x1b\x74\x06', # Simplified Kanji, Hirakana
                'CHARCODE_GREEK':  '\x1b\x74\x07', # Simplified Kanji
                'CHARCODE_HEBREW':  '\x1b\x74\x08', # Simplified Kanji
                'CHARCODE_PC1252':  '\x1b\x74\x11', # Western European Windows Code Set
                'CHARCODE_PC866':  '\x1b\x74\x12', # Cirillic #2
                'CHARCODE_PC852':  '\x1b\x74\x13', # Latin 2
                'CHARCODE_PC858':  '\x1b\x74\x14', # Euro
                'CHARCODE_THAI42':  '\x1b\x74\x15', # Thai character code 42
                'CHARCODE_THAI11':  '\x1b\x74\x16', # Thai character code 11
                'CHARCODE_THAI13':  '\x1b\x74\x17', # Thai character code 13
                'CHARCODE_THAI14':  '\x1b\x74\x18', # Thai character code 14
                'CHARCODE_THAI16':  '\x1b\x74\x19', # Thai character code 16
                'CHARCODE_THAI17':  '\x1b\x74\x1a', # Thai character code 17
                'CHARCODE_THAI18':  '\x1b\x74\x1b', # Thai character code 18
                'BARCODE_TXT_OFF':  '\x1d\x48\x00', ## Barcode format HRI barcode chars OFF
                'BARCODE_TXT_ABV':  '\x1d\x48\x01', # HRI barcode chars above
                'BARCODE_TXT_BLW':  '\x1d\x48\x02', # HRI barcode chars below
                'BARCODE_TXT_BTH':  '\x1d\x48\x03', # HRI barcode chars both above and below
                'BARCODE_FONT_A':  '\x1d\x66\x00', # Font type A for HRI barcode chars
                'BARCODE_FONT_B':  '\x1d\x66\x01', # Font type B for HRI barcode chars
                'BARCODE_HEIGHT':  '\x1d\x68\x64', # Barcode Height [1-255]
                'BARCODE_WIDTH':  '\x1d\x77\x03', # Barcode Width  [2-6]
                'BARCODE_UPC_A':  '\x1d\x6b\x00', # Barcode type UPC-A
                'BARCODE_UPC_E':  '\x1d\x6b\x01', # Barcode type UPC-E
                'BARCODE_EAN13':  '\x1d\x6b\x02', # Barcode type EAN13
                'BARCODE_EAN8':  '\x1d\x6b\x03', # Barcode type EAN8
                'BARCODE_CODE39':  '\x1d\x6b\x04', # Barcode type CODE39
                'BARCODE_ITF':  '\x1d\x6b\x05', # Barcode type ITF
                'BARCODE_NW7':  '\x1d\x6b\x06', # Barcode type NW7
                'S_RASTER_N':  '\x1d\x76\x30\x00', ## Image format Set raster image normal size
                'S_RASTER_2W':  '\x1d\x76\x30\x01', # Set raster image double width
                'S_RASTER_2H':  '\x1d\x76\x30\x02', # Set raster image double height
                'S_RASTER_Q':  '\x1d\x76\x30\x03', # Set raster image quadruple
                'PD_N50':  '\x1d\x7c\x00', ## Printing Density Printing Density -50%
                'PD_N37':  '\x1d\x7c\x01', # Printing Density -37.5%
                'PD_N25':  '\x1d\x7c\x02', # Printing Density -25%
                'PD_N12':  '\x1d\x7c\x03', # Printing Density -12.5%
                'PD_0':  '\x1d\x7c\x04', # Printing Density  0%
                'PD_P50':  '\x1d\x7c\x08', # Printing Density +50%
                'PD_P37':  '\x1d\x7c\x07', # Printing Density +37.5%
                'PD_P25':  '\x1d\x7c\x06', # Printing Density +25%
                'PD_P12':  '\x1d\x7c\x05', # Printing Density +12.5%
        }
        return matrixc

class EvaJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time, decimal types and UUIDs.
    """
    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime.datetime):
            r = o.strftime('%Y-%m-%d %H:%M:%S')
            return r
        elif isinstance(o, datetime.date):
            try:
                return o.strftime('%Y-%m-%d')
            except:
                return datetime.date.today().strftime('%Y-%m-%d')
        elif isinstance(o, datetime.time):
            if is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, Decimal):
            return float(o)
        elif isinstance(o, uuid.UUID):
            return str(o)
        elif isinstance(o, ImageFieldFile):
            try:
                return base64.b64encode(o.read())
            except:
                return ''
        else:
            return super(EvaJSONEncoder, self).default(o)
