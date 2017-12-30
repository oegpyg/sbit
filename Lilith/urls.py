from django.views.decorators.gzip import gzip_page
from django.views.decorators.csrf import csrf_exempt
from django.conf.urls import url
from Lilith.views import  (
                                        EpiCentro,
                                        show_file,
                                        execute_module,
                                        StructureTextTable,
                                        DinamicTemplate,
                                        JsonModel,
                                        JsonCache,
                                        ValidateDuplicate,
                                        ValidateForeign,
                                        AddRecord,
                                        AsignRecord,
                                        OperationRecord)

urlpatterns = (
    url(r'^$', gzip_page(EpiCentro.as_view()), name='epicentro'),
    #traer plantilla generica
    url(r'^dinamic_template/$', gzip_page(DinamicTemplate.as_view()), name='dinamic_template'),
    #imprimir en formato ascci (matriciales)
    url(r'^structure_text_table', csrf_exempt(StructureTextTable.as_view()), name='structure_text_table'),
    #mostrar pdf/archivos varios...
    url(r'^show_file/(?P<filename>[\w|\/\.]+)/$', show_file, name='show_file'),
    #operaciones crud generacion ADD, INACTIVE, ASIGNACION
    url(r'^add_record/$', csrf_exempt(AddRecord.as_view()), name='add_record'),
    url(r'^asign_record/$', csrf_exempt(AsignRecord.as_view()), name='asign_record'),
    url(r'^operation_record/$', csrf_exempt(OperationRecord.as_view()), name='operation_record'),
    #ejectuar modulos
    url(r'^execute_module', execute_module, name='execute_module'),
    #traer datos en formato json
    url(r'^get_jsonmodel/$', gzip_page(JsonModel.as_view()), name='get_jsonmodel'),
    #traer datos desde redis
    url(r'^get_jsoncache/$', gzip_page(JsonCache.as_view()), name='get_jsoncache'),
    #validaciones generacions, duplicidad...etc
    url(r'^validate_duplicate/$', gzip_page(csrf_exempt(ValidateDuplicate.as_view())), name='validate_duplicate'),
    url(r'^validate_foreign/$', gzip_page(csrf_exempt(ValidateForeign.as_view())), name='validate_foreign'),
)
