

a=[{'type': 'string_too_short', 'loc': ('body', 'client_id'), 'msg': 'String should have at least 6 characters', 'input': 'm', 'ctx': {'min_length': 6}}, {'type': 'string_too_short', 'loc': ('body', 'client_secret'), 'msg': 'String should have at least 8 characters', 'input': 'sup', 'ctx': {'min_length': 8}},{'type': 'string_too_short', 'loc': ('input', 'client_secret'), 'msg': 'String should have at least 8 characters', 'input': 'sup', 'ctx': {'min_length': 8}}]

# result = {error['loc'][0]: {error['loc'][1]: {key: error[key] for key in error if key != 'loc'} for error in a}}
# format = {loc[0]: {loc[1]: {key: error[key] for key in error if key != 'loc'} for error in a} for loc in [error['loc']] for error in a}
format={ 
       error['loc'][0]:{
       error['loc'][1]:{error['loc'][1]:{key:error[key] for key in error if key!='loc'}} 
    }
    for error in a}
for error in a:
    # print(error)
    _,field=error['loc']
    if _ not in  format:
        format[_]={}
    format[_][field] = {key:error[key] for key in error if key!='loc'}



#  formatError={}
#             for error in exc.errors():
#                 # print(error)
#                 _,field=error['loc']
#                 if _ not in  format:
#                     formatError[_]={}
#                 formatError[_][field] ={key:error[key] for key in error if key!='loc'}
result={
    "body":{
        "client_id":{
            'type': 'string_too_short',
            'msg': 'String should have at least 6 characters',
            'input': 'm',
            'ctx': {'min_length': 6}

        }
    }
}

{'body': {'client_id': {'type': 'string_too_short', 'msg': 'String should have at least 6 characters', 'input': 'm', 'ctx': {'min_length': 6}}, 'client_secret': {'type': 'string_too_short', 'msg': 'String should have at least 8 characters', 'input': 'sup', 'ctx': {'min_length': 8}}}, 'input': {'client_secret': {'type': 'string_too_short', 'msg': 'String should have at least 8 characters', 'input': 'sup', 'ctx': {'min_length': 8}}}}


print(format)