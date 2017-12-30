# -*- coding: utf-8 -*-
from Lilith.eva_manag import (EvaFormat,
                              EvaJSONEncoder,
                              EvaQuery)
from  lzstring import LZString
import math
from boltons.iterutils import  chunked
from htmlmin.minify import html_minify
from celery.execute import send_task
import uuid
import codecs
from django.forms import model_to_dict
import datetime
from django.views.generic import View
from django.utils.safestring import mark_safe
import os
import re
from urllib2 import unquote
import json
from django.apps import apps
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response, render, HttpResponse, Http404, redirect, resolve_url
from django.core.files import File
from django.views.decorators.csrf import csrf_exempt
import importlib
from django.core.cache import caches
from dashtable import html2rst

rdisc = caches['common-data']
get_model = apps.get_model
evaf = EvaFormat()
evaq = EvaQuery()


class EpiCentro(View):
    """Esta es la unica calse en todo sbits que sirve un tempalte"""
    def get(self, request):
        return render(request, 'EpiCentro.html')

class StructureTextTable(View):
    def post(self, request):
        """Convierte html a un formato RestructureText para impresiones a matriciales"""
        matrixcodes = evaf.mprinters_cods()
        lzs = LZString()
        html = request.POST.get('html')
        html = lzs.decompresFromBase64(html)
        html = html_minify(html)
        html =  re.sub(r'<(script).*?</\1>(?s)', '', html)
        html = re.sub('<button.*?</button>', '', html)
        html = re.sub('label|label-danger|label-warning|label-info|label-primary','', html)
        html = re.sub('<input .*?>', '', html)
        html = re.sub('<thead>', ' ', html)
        html = re.sub('</thead>', ' ', html)
        html = re.sub('<tfoot>', ' ', html)
        html = re.sub('</tfoot>', ' ', html)
        pk = request.POST.get('pk')
        papel = request.POST.get('papel')
        pagina = request.POST.get('pagina')
        if papel == 'a4':
            paper_length = 60
        if papel == 'letter':
            paper_length = 60
        if papel == 'legal':
            paper_length = 80
        orientacion = request.POST.get('orientacion')
        unique_print = int(uuid.uuid4())
        fpath = '/tmp/%s.html' % unique_print
        f = codecs.open(fpath, 'wb', encoding='utf-8')
        f.write(html)
        f.close()
        try:
            d = html2rst(fpath, force_headers=True)
        except:
            f = codecs.open(fpath, 'wb')
            f.write(html.replace('th', 'td').encode('ascii', errors='replace'))
            f.close()
            d = html2rst(fpath, force_headers=True)
        lines = d.splitlines()
        docud = chunked(lines, paper_length)
        if pagina:
            pages  = pagina.split(',')
            if len(pages) < 2:
                pages[0] = int(pages[0])
                ini = pages[0] - 1
                last = pages[0]
            else:
                ini, last = pages
                ini = int(ini)
                ini = int(last) - 1
            docud = docud[ini: last]
        btmp = []
        for idx, chung in enumerate(docud):
            for it in chung:
                btmp.append(it)
        btext = '\n'.join(btmp)
        if request.POST.get('fila'):
            btext = re.sub('[-]+\+', evaf.suppress_score, btext)
            if request.POST.get('espaciado'):
                btext = [ re.sub('^\+\s+[\+\s]+$', ' ', c) for c in btext.splitlines() ]
                btext = '\n'.join(btext)
        if request.POST.get('columna'):
            btext = btext.replace('|', ' ')
            btext = btext.replace('+', ' ')
        if not request.POST.get('espaciado'):
            btext = re.sub('\|\s+\|\s+\+', '', btext).replace('+',' ')
            # btext = '\n'.join([ c.rstrip() for c in btext.splitlines() if c.strip() ])
            btext = '\n'.join([ c.rstrip() for c in btext.splitlines() if c.strip() ])
        lines = btext.splitlines()
        bdata = []
        docud = chunked(lines, paper_length)
        for idx, chung in enumerate(docud):
            for it in chung:
                bdata.append(it)
            bdata.append(matrixcodes.get('CTL_FF'))
        btext = '\n'.join(bdata)

        fpathptr = '/tmp/%s.ptr' % unique_print
        ff = codecs.open(fpathptr, 'w', encoding='utf-8')
        ff.write(btext)
        ff.close()
        fpathtxt = '/tmp/%s.txt' % unique_print
        f = codecs.open(fpathtxt, 'wb', encoding='utf-8')
        f.write(btext)
        f.close()
        file_url =  evaf.url_viewfull('show_file', filename=fpathtxt)
        response = {'location_file': file_url}
        opciones = {'media': papel, 'orientation': orientacion}
        send_task('Lilith.tasks.imprimir_documento', kwargs={'opciones': opciones,  'fpath': fpathptr, 'pk': pk })
        return HttpResponse(json.dumps(response), content_type='application/javascript')

def show_file(request, filename):
    #TODO:
    try:
        wrapper = File(file('/%s' % filename))
    except Exception, e:
        return HttpResponse(json.dumps({'error': ['NO SE PUDO IMPRIMIR EL DOCUMENTO %s' % str(e)]}),
                            content_type='application/javascript' )
    #leer el archivo y encontrar el content_type
    response = HttpResponse(wrapper, content_type='application/image')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename.split('/')[-1]
    response['Content-Length'] = os.path.getsize('/%s' % filename)
    return response

@csrf_exempt
def execute_module(request):
    if request.method == 'POST':
        module_name = request.POST.get('module_name')
        class_name = request.POST.get('class_name')
        method_name = request.POST.get('method_name')
        jsonp = request.POST.get('jsonp')
        SbLModule = importlib.import_module(module_name)
        SbLClass = getattr(SbLModule, class_name)()
        SbLMethod = getattr(SbLClass, method_name)
        response = SbLMethod(request.user,query_dict=request.POST, files=request.FILES)
        if jsonp:
            jsondata = jsonp+'('+json.dumps(response, cls=EvaJSONEncoder)+');'
            return HttpResponse(jsondata, content_type='application/javascript')
        return HttpResponse(json.dumps(response, cls=EvaJSONEncoder), content_type='application/javascript')

class AddRecord(View):
    def post(self, request):
        ahora = datetime.datetime.now()
        userobj = request.request.user
        username = userobj.username
        files = request.FILES
        app_name = request.POST.get('app_name')
        model_name = request.POST.get('model_name')
        model_class = get_model(app_name, model_name)
        lookup = {}
        modelobj = None
        params = evaq.querydict_params(querylist=request.POST.lists())
        columns = params.keys()
        params.update({'StoreBy': username, 'StoreTime': ahora, })
        if request.POST.get('lookup'):
            lookup = json.loads(request.POST.get('lookup'))
            for fr in lookup.keys():
                params.pop(fr, None)
            columns = params.keys()
            for col in columns:
                if re.search('__', col):
                    fmodel, ffield = col.split('__')
                    field = model_class._meta.get_field(fmodel)
                    fparams = {'%s' % ffield: params.get(col) }
                    try:
                        foreignobj = field.rel.model.objects.get(**fparams)
                    except Exception, e:
                        response = {'error': 'Error En Datos  Relacionados {} {} {} {}'.format((unicode(e.message, 'utf-8'), fmodel, ffield, model_name))}
                        return HttpResponse(json.dumps(response), content_type='application/javascript')
                    params[fmodel] = foreignobj
                    params.pop(col)
                    continue
                field = model_class._meta.get_field(col)
                if field.is_relation:
                    try:
                        foreignobj = field.rel.model.objects.get(pk=params.get(col))
                    except Exception, e:
                        response = {'error': 'Error En Datos  Relacionados {} {} {}'.format((unicode(e.message, 'utf-8'), col, model_name))}
                        return HttpResponse(json.dumps(response), content_type='application/javascript')
                    params[col] =foreignobj
            try:
                model_class.objects.filter(**lookup).update(**params)
            except Exception, e:
                response = {'error': 'Error Actualizando {} {} {}'.format((unicode(e.message, 'utf-8'), lookup, model_name))}
                return HttpResponse(json.dumps(response), content_type='application/javascript')
            #only just for audit
            modelobj = model_class.objects.get(**lookup)
            modelobj.save()
            if files:
                cfiles = files.keys()
                for colf in cfiles:
                    fileform = files[colf]
                    setattr(modelobj, colf, fileform)
                    fielobj = getattr(modelobj, colf)
                    try:
                        fielobj.save(fileform.name, fileform)
                    except Exception, e:
                        response = {'error': 'Error Salvando Documentos {} {} {}'.format((unicode(e.message, 'utf-8'), colf, model_name))}
                        return HttpResponse(json.dumps(response), content_type='application/javascript')
            response = {'exitos': ['Alterado'], 'pk': modelobj.pk }
            return HttpResponse(json.dumps(response), content_type='application/javascript')
        #else we create a new one
        for col in columns:
            if re.search('__', col):
                fmodel, ffield = col.split('__')
                field = model_class._meta.get_field(fmodel)
                fparams = {'%s' % ffield: params.get(col) }
                try:
                    foreignobj = field.rel.model.objects.get(**fparams)
                except Exception, e:
                    response = {'error': 'Error En Datos  Relacionados {} {} {}'.format(unicode(e.message, 'utf-8'), col, model_name)}
                    return HttpResponse(json.dumps(response), content_type='application/javascript')
                params[fmodel] = foreignobj
                params.pop(col)
                continue
            field = model_class._meta.get_field(col)
            if field.is_relation:
                try:
                    foreignobj = field.rel.model.objects.get(pk=params.get(col))
                except Exception, e:
                    response = {'error': 'Error En Datos  Relacionados {} {} {}'.format(unicode(e.message, 'utf-8'), col, model_name)}
                    return HttpResponse(json.dumps(response), content_type='application/javascript')
                params[col] =foreignobj
        try:
            modelobj = model_class.objects.create(**params)
        except Exception, e:
            response = {'error': u'Error Creando Dato {} {}'.format(unicode(e.message, 'utf-8'), model_name)}
            return HttpResponse(json.dumps(response), content_type='application/javascript')

        if files:
            cfiles = files.keys()
            for colf in cfiles:
                fileform = files[colf]
                setattr(modelobj, colf, fileform)
                fielobj = getattr(modelobj, colf)
                try:
                    fielobj.save(fileform.name, fileform)
                except Exception, e:
                    response = {'error': 'Error Salvando Documentos {} {} {}'.format((unicode(e.message, 'utf-8'), colf, model_name))}
                    return HttpResponse(json.dumps(response), content_type='application/javascript')
        response = {'exitos': ['Creado'], 'pk': modelobj.pk }
        return HttpResponse(json.dumps(response), content_type='application/javascript')

class AsignRecord(View):
    def post(self, request):
        recieve_app_name = request.POST.get('recieve_app_name')
        recieve_model = request.POST.get('recieve_model')
        recieve_pks = request.POST.getlist('recieve_pk')
        recieve_attr = request.POST.get('recieve_attr')
        asign_app_name = request.POST.get('asign_app_name')
        asign_model = request.POST.get('asign_model')
        asign_pk = request.POST.get('asign_pk')
        recieve_model_class = get_model(recieve_app_name, recieve_model)
        asign_model_class = get_model(asign_app_name, asign_model)
        asign_modelobj = asign_model_class.objects.get(pk=asign_pk)
        pupdate = { '%s' % recieve_attr: asign_modelobj }
        recieve_model_class.objects.filter(pk__in=recieve_pks).update(**pupdate)
        response = {'Exitos': 'Actualizado'}
        return HttpResponse(json.dumps(response), content_type='application/javascript')

#Funcion generica que incluye las formas de realizar agregar, modificacion y anulacion, mediante pqgrid
##Los metodos lookups seguiran existiendo puesto que son una manera mas versatil de realizar trabajos por batchs
## pero esto es util para la generalidad de los casos
## esta generalidad tiene la de llamar metodos especificos por aplicacion, por ejemplo en la seccion de orders
class OperationRecord(View):
    def post(self, request):
        userobj = request.user
        files = request.FILES
        app_name = request.POST.get('app_name')
        model_name = request.POST.get('model_name')
        model_class = get_model(app_name, model_name)
        update_module_name = request.POST.get('update_module_name')
        deletelist = json.loads(request.POST.get('deleteList', '[]'))
        updatelist = json.loads(request.POST.get('updateList', '[]'))
        response = []
        if update_module_name:
           update_class_name = request.POST.get('update_class_name')
           update_method_name = request.POST.get('update_method_name')
           update_SbLModule = importlib.import_module(update_module_name)
           update_SbLClass = getattr(update_SbLModule, update_class_name)()
           update_SbLMethod = getattr(update_SbLClass, update_method_name)
        #delete method
        delete_module_name = request.POST.get('delete_module_name')
        if delete_module_name:
           delete_class_name = request.POST.get('delete_class_name')
           delete_method_name = request.POST.get('delete_method_name')
           delete_SbLModule = importlib.import_module(delete_module_name)
           delete_SbLClass = getattr(delete_SbLModule, delete_class_name)()
           delete_SbLMethod = getattr(delete_SbLClass, delete_method_name)
        # response = SbLMethod(request.user,query_dict=request.POST, files=request.FILES)
        #procesar anulacion
        ####CODE HERE
        for data in deletelist:
            if delete_module_name:
                # print 'ANULADO metodo %s' % (delete_SbLMethod)
                try:
                    response.append(delete_SbLMethod(userobj,query_dict=data, files=files))
                except Exception, e:
                    response.append({'error': e})
            else:
                # print 'ANULADO GENERICO'
                try:
                    response.append(inactive_record(userobj, data=data, model_class=model_class))
                except Exception, e:
                    response.append({'error': '%s %s %s' % (e.message, data.get('pq_cellcls'), data.get('lookup'))})
        #procesar actualizacion
        ####CODE HERE
        for data in updatelist:
            if update_module_name:
                # print 'UPDATE metodo %s' % (update_SbLMethod )
                try:
                    response.append(update_SbLMethod(userobj,query_dict=data, files=files))
                except Exception, e:
                    response.append({'error': e.message})
            else:
                # print 'UPDATE GENERICO'
                try:
                    response.append(update_record(userobj, data=data, model_class=model_class))
                except Exception, e:
                    response.append({'error': '%s %s %s' % (e.message, data.get('pq_cellcls'), data.get('lookup'))})
        #procesar carga
        ####CODE HERE
        return HttpResponse(json.dumps(response), content_type='application/javascript')

def update_record(*args, **kwargs):
        ahora = datetime.datetime.now()
        userobj = kwargs.get('user')
        username = userobj.username
        data = kwargs.get('data')
        lookup = data.get('lookup')
        pq_cellcls = data.get('pq_cellcls')
        model_class = kwargs.get('model_class')
        modelobj = model_class.objects.get(**lookup)
        columns = pq_cellcls.keys()
        params = {'StoreBy': username, 'StoreTime': ahora}
        cparams = {
                'NullBy': username, 'NullTime': ahora,
                'CheckBy': username, 'CheckTime': None,
                'PassBy': username, 'PassTime': ahora,
        }
        for col in columns:
            if re.search('__', col):
                if re.search('foreign', col):
                    fmodel, ffield, flookup = col.split('__')
                    field = model_class._meta.get_field(fmodel)
                    if re.search('lookup', col):
                        params = {'%s' % ffield: data.get(col) }
                    else:
                        params = {'pk': data.get(col) }
                    foreignobj = field.rel.model.objects.get(**params)
                    setattr(modelobj, fmodel, foreignobj)
                else:
                    fmodel, ffield = col.split('__')
                    field = getattr(modelobj, fmodel)
                    setattr(field, ffield,  data.get(col))
                    field.save()
            else:
                setattr(modelobj, col, data.get(col))
                if col == 'PassBy':
                    cparams['NullBy'] = False
                    cparams['CheckBy'] = username
                    cparams['CheckTime'] = ahora
                    cparams['PassBy'] = username
                    cparams['PassTime'] = ahora
                    for k, v in cparams.iteritems():
                        setattr(modelobj, k, v)
                if col == 'CheckBy':
                    cparams['NullBy'] = False
                    cparams['CheckBy'] = username
                    cparams['CheckTime'] = ahora
                    for k, v in cparams.iteritems():
                        setattr(modelobj, k, v)
                if col == 'NullBy':
                    cparams['NullBy'] = username
                    cparams['NullTime'] = ahora
                    cparams['PassBy'] = None
                    cparams['CheckBy'] = None
                    for k, v in cparams.iteritems():
                        setattr(modelobj, k, v)
        modelobj.save()
        return {'exitos': 'Actualizado Registro %s %s' % (kwargs.get('model_class'), lookup)}

def inactive_record(*args, **kwargs):
      ahora = datetime.datetime.now()
      userobj = kwargs.get('user')
      model_class = kwargs.get('model_class')
      data = kwargs.get('data')
      lookup = data.get('lookup')
      username = userobj.username
      params = {'NullBy': username, 'NullTime': ahora, 'CheckBy': None, 'PassBy': None }
      model_class.objects.filter(**lookup).update(**params)
      return {'exitos': 'Anulado Registro %s %s' % (kwargs.get('model_class'), lookup)}

class JsonModel(View):
    def get(self, request):
           """Traer via web un modelo en formato json, en el cual se pueda realizar queries
            http://192.168.1.13:8000/imp_man/get_jsonmodel/?key_name=salamanca&app_name=warehouse_man&model_name=palletsmanagmovimiento&model_key=palletsmanagmovimiento&recepcion=0
            http://192.168.1.13:8000/imp_man/get_jsonmodel/?key_name=salamanca&app_name=sales_man&model_name=prodmaestro&model_key=prodmaestro&prod_codigoviejo=5338
            http://192.168.1.13:8000/imp_man/get_jsonmodel/?key_name=salamanca&app_name=warehouse_man&model_name=ingresomercaderiaheader&model_key=ingreso_proforma
           """
           fm = format_cache.FormatCache()
           api_key = request.GET.get('api_key', '').strip()
           key_name = request.GET.get('key_name', '').strip()
           app_name = request.GET.get('app_name').strip()
           model_name = request.GET.get('model_name').strip()
           model_key = request.GET.get('model_key').strip()
           method_call = request.GET.get('method_call')
           distinct_value = request.GET.getlist('distinct_value')
           init = request.GET.get('init')
           last = request.GET.get('last')
           order_field = request.GET.getlist('order_field')
           type_datatable = request.GET.get('type_datatable')
           dparamquery = request.GET.get('dparamquery')
           jsonp = request.GET.get('jsonp')
           model_class = get_model(app_name, model_name)

           if dparamquery:
              pq_curpage = int(request.GET.get('pq_curpage'))
              pq_rpp = int(request.GET.get('pq_rpp'))



              params = utilitarios.querydict_params(request.GET.lists(), ['type_datatable', 'init', 'last', 'pq_datatype',
                                                                                                                    'pq_rpp', 'dparamquery', 'pq_curpage', 'pq_filter', 'pq_sort',
                                                                                                                    'callback', 'jsonp', 'explicit_key', 'order_field'
                                                                                                                    ])
              if request.GET.get('pq_filter'):
                  pqfilter = json.loads(request.GET.get('pq_filter'))
                  pquery = pqueryfilter(pqfilter)

                  params.update(utilitarios.querydict_params(pquery, ['type_datatable', 'init', 'last', 'pq_datatype',
                                                                                                                    'pq_rpp', 'dparamquery', 'pq_curpage', 'pq_filter', 'pq_sort',
                                                                                                                    'callback', 'jsonp', 'explicit_key', 'order_field'
                                                                                                                    ]) )

              q_search = utilitarios.querydict_args(request.GET.lists())
              # print params, q_search, 'QUERY'
              order_by = []
              if request.GET.get('pq_sort'):
                for order in json.loads(request.GET.get('pq_sort')):
                    okey = order.get('dataIndx')
                    direc = order.get('dir')
                    if direc == 'down':
                        okey = '-%s' % okey
                    order_by.append(okey.replace('__foreign', ''))
              records = model_class.objects.filter(*(q_search, ), **params).count()
              skip_records = abs((pq_rpp * (pq_curpage - 1)))
              # print skip_records, records, pq_curpage, pq_rpp, pq_rpp+skip_records
              # print skip_records, records, pq_curpage, pq_rpp, pq_rpp+skip_records
              if skip_records >= records:
                  pq_curpage = math.ceil(records / pq_rpp)
                  skip_records = abs((pq_rpp * (pq_curpage - 1)))
              bdict = {
                  'totalRecords': records,
                  'curPage': pq_curpage,
                  'data': []
              }
              for aobj in model_class.objects.filter(*(q_search, ), **params).order_by(*order_by)[skip_records:pq_rpp+skip_records]:
                md = fm.serial_model(aobj, model_key, explicit_key=True)
                # modeldict.append(md)
                bdict['data'].append(md)
              jsondata = json.dumps(bdict, cls=utilitarios.NetipaJSONEncoder)
              if jsonp:
                 jsondata = jsonp+'('+jsondata+');'
              return HttpResponse(jsondata, content_type='application/javascript')

           modeldict = []
           if key_name != 'salamanca':
              api_keyobj = get_object_or_404(ApiKeys, api_key=api_key)
              if not api_keyobj:
                 return HttpResponse(modeldict, content_type='application/javascript')
           params = utilitarios.querydict_params(request.GET.lists(), ['type_datatable', 'init', 'last', 'pq_datatype',                                                                                                                     'callback', 'jsonp', 'explicit_key', 'order_field'])
           q_search = utilitarios.querydict_args(request.GET.lists())
           # print params, q_search
           if method_call:
               if method_call == 'distinct':
                   resultiter = model_class.objects.filter(*(q_search, ), **params).distinct(*distinct_value)
                   for aobj in resultiter:
                         md = fm.serial_model(aobj, model_key, explicit_key=True)
                         modeldict.append(md)
                   if type_datatable:
                     mdictl = len(modeldict)
                     modeldict = {
                         "draw": 1,
                          "recordsTotal": mdictl,
                          "recordsFiltered": mdictl,
                          "data": modeldict
                      }

                   jsondata = json.dumps(modeldict, cls=utilitarios.NetipaJSONEncoder)
                   if jsonp:
                      jsondata = jsonp+'('+jsondata+');'
                   return HttpResponse(jsondata, content_type='application/javascript')

               if method_call == 'mlimit':
                   resultiter = model_class.objects.filter(*(q_search, ), **params)[int(init):int(last)]
                   for aobj in resultiter:
                         md = fm.serial_model(aobj, model_key, explicit_key=True)
                         modeldict.append(md)
                   if type_datatable:
                     mdictl = len(modeldict)
                     modeldict = {
                         "draw": 1,
                          "recordsTotal": mdictl,
                          "recordsFiltered": mdictl,
                          "data": modeldict
                      }
                   jsondata = json.dumps(modeldict, cls=utilitarios.NetipaJSONEncoder)
                   if jsonp:
                      jsondata = jsonp+'('+jsondata+');'
                   return HttpResponse(jsondata, content_type='application/javascript')

               if method_call == 'order_by':
                   resultiter = model_class.objects.filter(*(q_search, ), **params).order_by(*order_field)
                   for aobj in resultiter:
                         md = fm.serial_model(aobj, model_key, explicit_key=True)
                         modeldict.append(md)
                   if type_datatable:
                     mdictl = len(modeldict)
                     modeldict = {
                         "draw": 1,
                          "recordsTotal": mdictl,
                          "recordsFiltered": mdictl,
                          "data": modeldict
                      }
                   jsondata = json.dumps(modeldict, cls=utilitarios.NetipaJSONEncoder)
                   if jsonp:
                      jsondata = jsonp+'('+jsondata+');'
                   return HttpResponse(jsondata, content_type='application/javascript')

               if method_call == 'limit_order_by':
                   resultiter = model_class.objects.filter(*(q_search, ), **params).order_by('-%s'  % order_field[0])[int(init):int(last)]
                   for aobj in resultiter:
                         md = fm.serial_model(aobj, model_key, explicit_key=True)
                         modeldict.append(md)
                   if type_datatable:
                     mdictl = len(modeldict)
                     modeldict = {
                         "draw": 1,
                          "recordsTotal": mdictl,
                          "recordsFiltered": mdictl,
                          "data": modeldict
                      }
                   jsondata = json.dumps(modeldict, cls=utilitarios.NetipaJSONEncoder)
                   if jsonp:
                      jsondata = jsonp+'('+jsondata+');'
                   return HttpResponse(jsondata, content_type='application/javascript')

               if method_call == 'getlast':
                   resultiter = model_class.objects.filter(*(q_search, ), **params).order_by('-%s' % order_field[0])
                   if resultiter:
                        fs = fm.serial_model(resultiter[0], model_key, explicit_key=True)
                        jsondata = json.dumps(fs, cls=utilitarios.NetipaJSONEncoder)
                        if jsonp:
                           jsondata = jsonp+'('+jsondata+');'
                        return HttpResponse(jsondata, content_type='application/javascript')
                   for aobj in resultiter:
                         md = fm.serial_model(aobj, model_key, explicit_key=True)
                         modeldict.append(md)
                   if type_datatable:
                     mdictl = len(modeldict)
                     modeldict = {
                         "draw": 1,
                          "recordsTotal": mdictl,
                          "recordsFiltered": mdictl,
                          "data": modeldict
                      }
                   jsondata = json.dumps(modeldict, cls=utilitarios.NetipaJSONEncoder)
                   if jsonp:
                      jsondata = jsonp+'('+jsondata+');'
                   return HttpResponse(jsondata, content_type='application/javascript')

               if method_call == 'getpks':
                    qset = list(model_class.objects.filter(*(q_search,), **params).values_list('pk', flat=True).order_by('pk'))
                    jsondata = json.dumps({method_call: qset }, cls=utilitarios.NetipaJSONEncoder)
                    if jsonp:
                       jsondata = jsonp+'('+jsondata+');'
                    return HttpResponse(jsondata, content_type='application/javascript')

               qset = model_class.objects.filter(*(q_search,), **params)
               mreps = getattr(qset, method_call)()
               jsondata = json.dumps({method_call: mreps }, cls=utilitarios.NetipaJSONEncoder)
               if jsonp:
                  jsondata = jsonp+'('+jsondata+');'
               return HttpResponse(jsondata, content_type='application/javascript')
           for aobj in model_class.objects.filter(*(q_search, ), **params):
                 md = fm.serial_model(aobj, model_key, explicit_key=True)
                 modeldict.append(md)
           if type_datatable:
             mdictl = len(modeldict)
             modeldict = {
                 "draw": 1,
                  "recordsTotal": mdictl,
                  "recordsFiltered": mdictl,
                  "data": modeldict
              }
           jsondata = json.dumps(modeldict, cls=utilitarios.NetipaJSONEncoder)
           if jsonp:
              jsondata = jsonp+'('+jsondata+');'
           return HttpResponse(jsondata, content_type='application/javascript')

class DinamicTemplate(View):
    def get(self, request):
        template_name = request.GET.get('template')
        query_dict = request.GET.dict()
        app_name = request.GET.get('app_name')
        model_name = request.GET.get('model_name')
        multipleobjs = request.GET.get('multipleobjs')
        dinamic_attrs = request.GET.get('dinamic_attrs')
        serial_model = request.GET.get('serial_model')
        fm = format_cache.FormatCache()
        if dinamic_attrs:
            query_dict.update(json.loads(unquote(dinamic_attrs)))
        if app_name and model_name:
            model_class = get_model(app_name, model_name)
            if multipleobjs:
                params = utilitarios.querydict_params(request.GET.lists(), ['multipleobjs', 'template', 'dinamic_attrs'])
                # print params
                modelobjs = model_class.objects.filter(**params)
                query_dict.update({'modelobjs': modelobjs })
                if serial_model:
                    serial_model  = [  fm.serial_model(m, serial_model) for m in modelobjs]
                    query_dict.update({'mdicts': json.dumps(serial_model, cls=utilitarios.NetipaJSONEncoder) })
            else:
                modelobj = model_class.objects.get(pk=request.GET.get('pk'))
                mdict = model_to_dict(modelobj)
                for field in modelobj._meta.fields:
                    if field.get_internal_type() == 'FileField':
                        fieldobj = getattr(modelobj, field.name)
                        if fieldobj:
                            mdict[field.name] = getattr(fieldobj, 'url')
                        else:
                            mdict[field.name] = '/static/img/null'
                modeldict = json.dumps(mdict, cls=utilitarios.NetipaJSONEncoder)
                query_dict.update({'modelobj': modelobj, 'modeldict': modeldict })
                if serial_model:
                    serial_model  = fm.serial_model(modelobj, serial_model)
                    query_dict.update({'mdict': json.dumps(serial_model, cls=utilitarios.NetipaJSONEncoder) })
        return render(request, template_name, query_dict)

class JsonCache(View):
    def get(self, request):
        cache_name = request.GET.get('cache_key')
        return HttpResponse(json.dumps(rdisc.get(cache_name), cls=utilitarios.NetipaJSONEncoder),   content_type='application/javascript')

class ValidateDuplicate(View):
    def post(self, request):
        model_name = request.POST.get('model_name')
        app_name = request.POST.get('app_name')
        model_class = get_model(app_name, model_name)
        excludeparams = {}
        excludepk = request.POST.get('excludepk')
        if excludepk:
            excludeparams['pk'] = excludepk
        # params = {'%s' % field: value }
        params = utilitarios.querydict_params(request.POST.lists(), ['type_datatable', 'excludepk'])
        if model_class.objects.filter(**params).exclude(**excludeparams):
            return HttpResponse(json.dumps('Valor Duplicado %s' % params) ,   content_type='application/javascript')
        return HttpResponse(json.dumps(True, cls=utilitarios.NetipaJSONEncoder),   content_type='application/javascript')

class ValidateForeign(View):
    def post(self, request):
        model_name = request.POST.get('model_name')
        app_name = request.POST.get('app_name')
        model_class = get_model(app_name, model_name)
        # params = {'%s' % field: value }
        params = utilitarios.querydict_params(request.POST.lists(), ['type_datatable', 'excludepk'])
        columns = params.keys()
        for col in columns:
            if re.search('__', col):
                foreign, field = col.split('__')
                fparams = {'%s' % field: params.get(col)}
        # print fparams
        if model_class.objects.filter(**fparams):
            return HttpResponse(json.dumps(True, cls=utilitarios.NetipaJSONEncoder),   content_type='application/javascript')
        return HttpResponse(json.dumps('Valor no Existe en %s' % model_name) ,   content_type='application/javascript')

