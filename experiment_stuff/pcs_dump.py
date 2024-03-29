# run to generate a file called data_experiment.pkl
# used by plot_any_shot_fully.py

# requires module load toksearch

from toksearch import PtDataSignal, MdsSignal, Pipeline
import numpy as np
import collections
import pprint
import pickle

import sys
import os

from scipy import interpolate

sys.path.append(os.path.join(os.path.dirname(__file__),'../lib'))
from transport_helpers import my_interp, interp_ND_rectangular
import fit_functions
from plot_tools import plot_comparison_over_time, plot_2d_comparison


import matplotlib.pyplot as plt

###### USER INPUTS ######
#                       #

#shots=np.load('shots.npy')
shots = [187076] #np.arange(187065,187080) #[187066,187068,187069] #[917609] #[185769] #[163303,175970] #175970 is Colin's good modulation shot; 154764 is David Eldon's

tmin = -2000
tmax = 5000

output_file='data_experiment.pkl' #/cscratch/abbatej/new_big_ml_data_run/data.pkl'

time_step=50

debug=False
debug_sig_name='cer_rot'

scalar_sig_names=['etswchprop']
for sig in ['etsinpwr','etsintor','etsinden','etsincur']:
    for i in range(7):
        scalar_sig_names.append('{}{}'.format(sig,i))
#['dstdenp','dssdenest','iptipp']
#'bt','DUSTRIPPED','ip','N1ICWMTH','N1IIWMTH','echpwr','dsifbonoff']
stability_sig_names=[] #['n1rms']
nb_sig_names=[] #['pinj','tinj']

efit_profile_sig_names=['pres','qpsi'] #['qpsi','pres']
efit_scalar_sig_names=[] #['li','aminor','kappa','tritop','tribot','volume']

efit_type='EFITRT2'

include_psirz=True
include_rhovn=True

thomson_sig_names=['temp','density'] #['density', 'temp']
thomson_scale={'density': 1e19, 'temp': 1e3}
include_thomson_uncertainty=True
thomson_areas=['CORE','TANGENTIAL']

cer_sig_names=[] #['rot'] #['temp','rot']
cer_scale={'temp': 1e3, 'rot': 1}
cer_type='cerquick'
cer_areas=['TANGENTIAL', 'VERTICAL']
cer_channels={'TANGENTIAL': np.arange(9,25), #1,33
              'VERTICAL': []} #np.arange(1,49)}

zipfit_sig_names=['etempfit','edensfit'] #['trotfit','edensfit','etempfit'] #,'itempfit'] #,'idensfit']

zipfit_pairs={'cer_temp': 'itempfit',
              'cer_rot': 'trotfit',
              'thomson_temp': 'etempfit',
              'thomson_density': 'edensfit'}

# our PCS algo stuff
pcs_sig_names=['etste', 'etstein', 'etsteout','etsne','etsnein','etsneout',
               'etsinprs','etspout', 'etsinq','etsqout']
# pcs_sig_names=['etste', 'etsne','etscr','etsct',
#                 'etstein', 'etsnein','etscrin', 'etsctin','etsinq', 'etsinprs',
#                 'etsteout', 'etsneout', 'etsqout', 'etspout','etsrout']

#['ftscrot','ftscpsin','ftsc1vld','ftsspsin','ftssrot','etscr','etscrin','etscrout','etsct','etsctin']
# ['etste', 'etsne','etscr','etsct',
#                'etstein', 'etsnein','etscrin', 'etsctin','etsinq', 'etsinprs',
#                'etsteout', 'etsneout', 'etsqout', 'etsprsout',
#                'etste', 'etsne','etscr','etsct']

pcs_length={sig_name: np.arange(0,33) for sig_name in pcs_sig_names}
pcs_length['ftscrot']=np.arange(1,16)
pcs_length['ftscpsin']=np.arange(1,16)
pcs_length['ftsc1vld']=np.arange(1,16)
pcs_length['ftsspsin']=np.arange(1,76)
pcs_length['ftssrot']=np.arange(1,76)

# psi
standard_x=np.linspace(0,1,65)

fit_function_dict={'linear_interp_1d': fit_functions.linear_interp_1d,
                   'spline_1d': fit_functions.spline_1d,
                   'nn_interp_2d': fit_functions.nn_interp_2d,
                   'linear_interp_2d': fit_functions.linear_interp_2d,
                   'mtanh_1d': fit_functions.mtanh_1d,
                   'csaps_1d': fit_functions.csaps_1d,
                   'rbf_interp_2d': fit_functions.rbf_interp_2d}
fit_functions_1d=['linear_interp_1d', 'mtanh_1d','spline_1d','csaps_1d']
fit_functions_2d=['nn_interp_2d','linear_interp_2d','rbf_interp_2d']

trial_fits=['linear_interp_1d','mtanh_1d'] #,'mtanh_1d', 'csaps_1d']

name_map={'standard_time': 'time',
          'zipfit_trotfit_rhon_basis': 'rotation',
          'zipfit_itempfit_rhon_basis': 'itemp',
          'zipfit_etempfit_rhon_basis': 'temp',
          'zipfit_edensfit_rhon_basis': 'dens',
          'aminor': 'a_{}'.format(efit_type),
          'li': 'li_{}'.format(efit_type),
          'kappa': 'kappa_{}'.format(efit_type),
          'volume': 'volume_{}'.format(efit_type),
          'tritop': 'triangularity_top_{}'.format(efit_type),
          'tribot': 'triangularity_bot_{}'.format(efit_type),
          'qpsi': 'q_{}'.format(efit_type),
          'pres': 'press_{}'.format(efit_type),
          'pinj': 'pinj',
          'tinj': 'tinj',
          'dstdenp': 'target_density',
          'dssdenest': 'density_estimate',
          'iptipp': 'curr_target',
          'echpwr': 'ech',
          'dsifbonoff': 'gas_feedback',
          'DUSTRIPPED': 'dud_trip',
          'bt': 'bt',
          'ip': 'curr',
          'N1ICWMTH': 'C_coil_method',
          'N1IIWMTH': 'I_coil_method'}

#                       #
#### END USER INPUTS ####


#### START OF SCRIPT ####
#                       #

#### GATHER DATA ####

pipeline = Pipeline(shots)

def standardize_time(old_signal,old_timebase,standard_times,
                     causal=True, window_size=50,
                     exponential_falloff=False, falloff_rate=100):
    new_signal=[]
    for i in range(len(standard_times)):
        if causal:
            inds_in_range=np.where(np.logical_and(old_timebase>=standard_times[i]-window_size,old_timebase<standard_times[i]))[0]
        else:
            inds_in_range=np.where(np.logical_and(old_timebase>=standard_times[i]-window_size,old_timebase<standard_times[i]+window_size))[0]
        if len(inds_in_range)==0:
            if len(old_signal.shape)==1:
                new_signal.append(np.nan)
            else:
                new_signal.append(np.full(old_signal.shape[1:],np.nan))
        else:
            if exponential_falloff:
                weights=np.array([np.exp(- np.abs(standard_times[i]-old_timebase[ind]) / falloff_rate) for ind in inds_in_range])
                weights/=sum(weights)
                new_signal.append( np.array( np.sum( [old_signal[ind]*weights[j] for j,ind in enumerate(inds_in_range)], axis=0) ) )
            else:
                new_signal.append(np.mean(old_signal[inds_in_range],axis=0))
    return np.array(new_signal)

######## FETCH SCALARS #############
for sig_name in scalar_sig_names:
    signal=PtDataSignal(sig_name)
    pipeline.fetch('{}_full'.format(sig_name),signal)

######## FETCH STABILITY #############
for sig_name in stability_sig_names:
    signal=MdsSignal('.MIRNOV.{}'.format(sig_name),
                     'MHD',
                     location='remote://atlas.gat.com')
    pipeline.fetch('{}_full'.format(sig_name),signal)


######## FETCH SCALARS #############
for sig_name in nb_sig_names:
    signal=MdsSignal(sig_name,
                     'NB',
                     location='remote://atlas.gat.com')
    pipeline.fetch('{}_full'.format(sig_name),signal)

######## FETCH EFIT PROFILES #############
for sig_name in efit_profile_sig_names:
    signal=MdsSignal('RESULTS.GEQDSK.{}'.format(sig_name),
                     efit_type,
                     location='remote://atlas.gat.com',
                     dims=['psi','times'])
    pipeline.fetch('{}_full'.format(sig_name),signal)

######## FETCH EFIT PROFILES #############
for sig_name in efit_scalar_sig_names:
    signal=MdsSignal('RESULTS.AEQDSK.{}'.format(sig_name),
                     efit_type,
                     location='remote://atlas.gat.com')
    pipeline.fetch('{}_full'.format(sig_name),signal)


######## FETCH PSIRZ   #############
if include_psirz:
    psirz_sig = MdsSignal(r'\psirz',
                          efit_type,
                          location='remote://atlas.gat.com',
                          dims=['r','z','times'])
    pipeline.fetch('psirz_full',psirz_sig)
    ssimag_sig = MdsSignal(r'\ssimag',
                          efit_type,
                          location='remote://atlas.gat.com')
    pipeline.fetch('ssimag_full',ssimag_sig)
    ssibry_sig = MdsSignal(r'\ssibry',
                          efit_type,
                          location='remote://atlas.gat.com')
    pipeline.fetch('ssibry_full',ssibry_sig)

######## FETCH RHOVN ###############
if include_rhovn:
    rhovn_sig = MdsSignal(r'\rhovn',
                          efit_type,
                          location='remote://atlas.gat.com',
                          dims=['psi','times'])
    pipeline.fetch('rhovn_full',rhovn_sig)

######## FETCH THOMSON #############
for sig_name in thomson_sig_names:
    for thomson_area in thomson_areas:
        thomson_sig = MdsSignal(r'TS.BLESSED.{}.{}'.format(thomson_area,sig_name),
                                'ELECTRONS',
                                location='remote://atlas.gat.com',
                                dims=('times','position'))
        pipeline.fetch('thomson_{}_{}_full'.format(thomson_area,sig_name),thomson_sig)
        if include_thomson_uncertainty:
            thomson_error_sig = MdsSignal(r'TS.BLESSED.{}.{}_E'.format(thomson_area,sig_name),
                                          'ELECTRONS',
                                          location='remote://atlas.gat.com')
            pipeline.fetch('thomson_{}_{}_uncertainty_full'.format(thomson_area,sig_name),thomson_error_sig)

######## FETCH CER     #############
if len(cer_sig_names)>0:
    for cer_area in cer_areas:
        for channel in cer_channels[cer_area]:
            cer_R_sig = MdsSignal('CER.{}.{}.CHANNEL{:02d}.R'.format(cer_type,
                                                                     cer_area,
                                                                     channel),
                                  'IONS',
                                  location='remote://atlas.gat.com')
            pipeline.fetch('cer_{}_{}_R_full'.format(cer_area,channel),cer_R_sig)
            cer_Z_sig = MdsSignal('CER.{}.{}.CHANNEL{:02d}.Z'.format(cer_type,
                                                                     cer_area,
                                                                     channel),
                                  'IONS',
                                  location='remote://atlas.gat.com')
            pipeline.fetch('cer_{}_{}_Z_full'.format(cer_area,channel),cer_Z_sig)

            for sig_name in cer_sig_names:
                correction=''
                if sig_name=='rot':
                    correction='c'
                cer_sig = MdsSignal('CER.{}.{}.CHANNEL{:02d}.{}'.format(cer_type,
                                                                        cer_area,
                                                                        channel,
                                                                        sig_name+correction),
                                    'IONS',
                                    location='remote://atlas.gat.com')
                pipeline.fetch('cer_{}_{}_{}_full'.format(cer_area,sig_name,channel),cer_sig)
                cer_error_sig = MdsSignal('CER.{}.{}.CHANNEL{:02d}.{}_ERR'.format(cer_type,
                                                                                  cer_area,
                                                                                  channel,
                                                                                  sig_name),
                                          'IONS',
                                          location='remote://atlas.gat.com')
                pipeline.fetch('cer_{}_{}_{}_error_full'.format(cer_area,sig_name,channel),cer_error_sig)


######## FETCH ZIPFIT ##############
for sig_name in zipfit_sig_names:
    zipfit_sig = MdsSignal(r'\ZIPFIT01::TOP.PROFILES.{}'.format(sig_name),'ZIPFIT01',location='remote://atlas.gat.com',dims=['rhon','times'])
    pipeline.fetch('zipfit_{}_full'.format(sig_name),zipfit_sig)

######## FETCH OUR PCS ALGO STUFF #############
for sig_name in pcs_sig_names:
    for i in pcs_length[sig_name]:
        pcs_sig = PtDataSignal('{}{}'.format(sig_name,i))
        pipeline.fetch('{}{}_full'.format(sig_name,i),pcs_sig)

@pipeline.map
def add_timebase(record):
    standard_times=np.arange(tmin,tmax,time_step)
    record['standard_time']=standard_times

@pipeline.map
def change_timebase(record):
    all_sig_names=efit_profile_sig_names+efit_scalar_sig_names+nb_sig_names+scalar_sig_names+stability_sig_names
    for sig_name in all_sig_names:
        try:
            record[sig_name]=standardize_time(record['{}_full'.format(sig_name)]['data'],
                                              record['{}_full'.format(sig_name)]['times'],
                                              record['standard_time'])
        except:
            print('missing {}'.format(sig_name))

if include_psirz:
    @pipeline.map
    def add_psin(record):
        psi_norm_f = record['ssibry_full']['data'] - record['ssimag_full']['data']
        # Prevent divide by 0 error by replacing 0s in the denominator
        problems = psi_norm_f == 0
        psi_norm_f[problems] = 1.
        record['psirz'] = (record['psirz_full']['data'] - record['ssimag_full']['data'][:, np.newaxis, np.newaxis]) / psi_norm_f[:, np.newaxis, np.newaxis]
        record['psirz'][problems] = 0

        record['psirz']=standardize_time(record['psirz'],
                                              record['psirz_full']['times'],
                                              record['standard_time'])
        record['psirz_r']=record['psirz_full']['r']
        record['psirz_z']=record['psirz_full']['z']

if include_rhovn:
    @pipeline.map
    def add_rhovn(record):
        record['rhovn']=standardize_time(record['rhovn_full']['data'],
                                         record['rhovn_full']['times'],
                                         record['standard_time'])

@pipeline.map
def zipfit_rhovn_to_psin(record):
    for sig_name in zipfit_sig_names:
        record['zipfit_{}_rhon_basis'.format(sig_name)]=standardize_time(record['zipfit_{}_full'.format(sig_name)]['data'],
                                                                   record['zipfit_{}_full'.format(sig_name)]['times'],
                                                                   record['standard_time'])

        rho_to_psi=[my_interp(record['rhovn'][time_ind],
                              record['rhovn_full']['psi']) for time_ind in range(len(record['standard_time']))]
        record['zipfit_{}_psi'.format(sig_name)]=[]
        for time_ind in range(len(record['standard_time'])):
            record['zipfit_{}_psi'.format(sig_name)].append(rho_to_psi[time_ind](record['zipfit_{}_full'.format(sig_name)]['rhon']))
        record['zipfit_{}_psi'.format(sig_name)]=np.array(record['zipfit_{}_psi'.format(sig_name)])

        zipfit_interp=fit_function_dict['linear_interp_1d']
        record['zipfit_{}'.format(sig_name)]=zipfit_interp(record['zipfit_{}_psi'.format(sig_name)],
                                                           record['standard_time'],
                                                           record['zipfit_{}_rhon_basis'.format(sig_name)],
                                                           np.ones(record['zipfit_{}_rhon_basis'.format(sig_name)].shape),
                                                           standard_x)
#        record['zipfit_{}'.format(sig_name)]=record['zipfit_{}_full'.format(sig_name)]

@pipeline.map
def map_thomson_1d(record):
    # an rz interpolator for each standard time
    r_z_to_psi=[interpolate.interp2d(record['psirz_r'],
                                     record['psirz_z'],
                                     record['psirz'][time_ind]) for time_ind in range(len(record['standard_time']))]

    for sig_name in thomson_sig_names:
        value=[]
        psi=[]
        uncertainty=[]
        for thomson_area in thomson_areas:
            for channel in range(len(record['thomson_{}_{}_full'.format(thomson_area,sig_name)]['position'])):
                value.append(standardize_time(record['thomson_{}_{}_full'.format(thomson_area,sig_name)]['data'][channel],
                                              record['thomson_{}_{}_full'.format(thomson_area,sig_name)]['times'],
                                              record['standard_time']))
                if thomson_area=='TANGENTIAL':
                    r=record['thomson_{}_{}_full'.format(thomson_area,sig_name)]['position'][channel]
                    z=0
                elif thomson_area=='CORE':
                    z=record['thomson_{}_{}_full'.format(thomson_area,sig_name)]['position'][channel]
                    r=1.94
                psi.append([r_z_to_psi[time_ind](r,z)[0] for time_ind in range(len(record['standard_time']))])
                if include_thomson_uncertainty:
                    uncertainty.append(standardize_time(record['thomson_{}_{}_uncertainty_full'.format(thomson_area,sig_name)]['data'][channel],
                                              record['thomson_{}_{}_uncertainty_full'.format(thomson_area,sig_name)]['times'],
                                              record['standard_time']))

        value=np.array(value).T/thomson_scale[sig_name]
        psi=np.array(psi).T
        value[np.isclose(value,0)]=np.nan
        if include_thomson_uncertainty:
            uncertainty=np.array(uncertainty).T/thomson_scale[sig_name]
            value[np.isclose(uncertainty,0)]=np.nan
        else:
            uncertainty=np.ones(np.shape(value))
        record['thomson_{}_raw_1d'.format(sig_name)]=value
        record['thomson_{}_uncertainty_raw_1d'.format(sig_name)]=uncertainty
        record['thomson_{}_psi_raw_1d'.format(sig_name)]=psi
        for trial_fit in trial_fits:
            if trial_fit in fit_functions_1d:
                record['thomson_{}_{}'.format(sig_name,trial_fit)] = fit_function_dict[trial_fit](psi,record['standard_time'],value,uncertainty,standard_x)

@pipeline.map
def map_cer_1d(record):
    # an rz interpolator for each standard time
    r_z_to_psi=[interpolate.interp2d(record['psirz_r'],
                                     record['psirz_z'],
                                     record['psirz'][time_ind]) for time_ind in range(len(record['standard_time']))]

    for sig_name in cer_sig_names:
        value=[]
        psi=[]
        error=[]
        for cer_area in cer_areas:
            for channel in cer_channels[cer_area]:
                if record['cer_{}_{}_{}_full'.format(cer_area,sig_name,channel)] is not None:
                    r=standardize_time(record['cer_{}_{}_R_full'.format(cer_area,channel)]['data'],
                                       record['cer_{}_{}_{}_full'.format(cer_area,sig_name,channel)]['times'],
                                       record['standard_time'])
                    z=standardize_time(record['cer_{}_{}_Z_full'.format(cer_area,channel)]['data'],
                                       record['cer_{}_{}_{}_full'.format(cer_area,sig_name,channel)]['times'],
                                       record['standard_time'])

                    value.append(standardize_time(record['cer_{}_{}_{}_full'.format(cer_area,sig_name,channel)]['data'],
                                                  record['cer_{}_{}_{}_full'.format(cer_area,sig_name,channel)]['times'],
                                                  record['standard_time']))
                    if sig_name=='rot':
                        value[-1]=np.divide(value[-1],r)
                    psi.append([r_z_to_psi[time_ind](r[time_ind],z[time_ind])[0] \
                                for time_ind in range(len(record['standard_time']))])
                    error.append(standardize_time(record['cer_{}_{}_{}_error_full'.format(cer_area,sig_name,channel)]['data'],
                                                  record['cer_{}_{}_{}_error_full'.format(cer_area,sig_name,channel)]['times'],
                                                  record['standard_time']))
        value=np.array(value).T/cer_scale[sig_name]
        psi=np.array(psi).T
        error=np.array(error).T
        value[np.where(error==1)]=np.nan
        uncertainty=np.ones(np.shape(value))
        record['cer_{}_raw_1d'.format(sig_name)]=value
        record['cer_{}_uncertainty_raw_1d'.format(sig_name)]=uncertainty
        record['cer_{}_psi_raw_1d'.format(sig_name)]=psi
        for trial_fit in trial_fits:
            if trial_fit in fit_functions_1d:
                record['cer_{}_{}'.format(sig_name,trial_fit)] = fit_function_dict[trial_fit](psi,record['standard_time'],value,uncertainty,standard_x)

@pipeline.map
def pcs_processing(record):
    for sig_name in pcs_sig_names:
        record['{}'.format(sig_name)]=[]
        for i in pcs_length[sig_name]:
            nonzero_inds=np.nonzero(record['{}{}_full'.format(sig_name,i)]['data'])
            record['{}'.format(sig_name)].append(standardize_time(record['{}{}_full'.format(sig_name,i)]['data'][nonzero_inds],
                                                                  record['{}{}_full'.format(sig_name,i)]['times'][nonzero_inds],
                                                                  record['standard_time']))

#needed_sigs=[sig_name for sig_name in all_sig_names]
needed_sigs=[]
needed_sigs+=[sig_name for sig_name in scalar_sig_names]
needed_sigs+=[sig_name for sig_name in nb_sig_names]
needed_sigs+=[sig_name for sig_name in efit_profile_sig_names]
needed_sigs+=[sig_name for sig_name in efit_scalar_sig_names]
needed_sigs+=[sig_name for sig_name in stability_sig_names]
needed_sigs+=[sig_name for sig_name in pcs_sig_names]
if False: #include_psirz:
    needed_sigs+=['psirz','psirz_r','psirz_z']
if include_rhovn:
    needed_sigs+=['rhovn']

for trial_fit in trial_fits:
    needed_sigs+=['cer_{}_{}'.format(sig_name,trial_fit) for sig_name in cer_sig_names]
    needed_sigs+=['thomson_{}_{}'.format(sig_name,trial_fit) for sig_name in thomson_sig_names]
needed_sigs+=['zipfit_{}'.format(sig_name) for sig_name in zipfit_sig_names]
####### TAKE THIS OUT FOR NEWER MODELS, UNCOMMENT ABOVE ############
#needed_sigs+=['zipfit_{}_rhon_basis'.format(sig_name) for sig_name in zipfit_sig_names]
#needed_sigs+=['zipfit_{}_full'.format(sig_name) for sig_name in zipfit_sig_names]
#needed_sigs+=['pinj_full','dstdenp_full','iptipp_full','volume_full','tinj_full']
#needed_sigs+=['n1rms_full']
###############################################
needed_sigs.append('standard_time')
if debug:
    needed_sigs.append('{}_psi_raw_1d'.format(debug_sig_name))
    needed_sigs.append('{}_raw_1d'.format(debug_sig_name))
    needed_sigs.append('{}_uncertainty_raw_1d'.format(debug_sig_name))
#pipeline.keep(needed_sigs)

records=pipeline.compute_serial()


final_data={}
for i in range(len(records)):
    record=records[i]
    shot=int(record['shot'])
    final_data[shot]={}
    final_data[shot]['t_ip_flat']=np.array(tmin)
    final_data[shot]['ip_flat_duration']=np.array(tmax)
    #final_data[shot]['topology']='SNB'
    for sig in record.keys():
        if sig in name_map:
            # for handling zipfit
            if 'rhon_basis' in sig:
                final_data[shot][name_map[sig]]=[]
                rhon=record['zipfit_{}_full'.format('etempfit')]['rhon']
                for time_ind in range(len(record['standard_time'])):
                    rho_to_zipfit=my_interp(rhon,
                                            record[sig][time_ind])
                    final_data[shot][name_map[sig]].append(rho_to_zipfit(standard_x))
                final_data[shot][name_map[sig]]=np.array(final_data[shot][name_map[sig]])
            else:
                final_data[shot][name_map[sig]]=np.array(record[sig])
                if name_map[sig]=='curr_target':
                    final_data[shot][name_map[sig]]=final_data[shot][name_map[sig]]*.5e6
        else:
            final_data[shot][sig]=np.array(record[sig])
    # to accomodate the old code's bug of flipping top and bottom
    if False:
        tmp=final_data[shot]['triangularity_top_EFIT01'].copy()
        final_data[shot]['triangularity_top_EFIT01']=final_data[shot]['triangularity_bot_EFIT01'].copy()
        final_data[shot]['triangularity_bot_EFIT01']=tmp
        final_data[shot]['pinj_full']=record['pinj_full']
        final_data[shot]['tinj_full']=record['tinj_full']
        final_data[shot]['iptipp_full']=record['iptipp_full']
        final_data[shot]['iptipp_full']['data']*=.5e6
        final_data[shot]['dstdenp_full']=record['dstdenp_full']
        final_data[shot]['volume_full']=record['volume_full']
        final_data[shot]['n1rms_full']=record['n1rms_full']


with open(output_file,'wb') as f:
    pickle.dump(final_data, f)

if debug:
    for shot in final_data:
        print(shot)
        print(final_data[shot].keys())
#    print(records[0]['cer_VERTICAL_temp_20_full'])
    #print('errors: ')
    #print(records[0]['errors'])
    if 'thomson' in debug_sig_name or 'cer' in debug_sig_name:
        xlist=[records[0]['{}_psi_raw_1d'.format(debug_sig_name)]]
        ylist=[records[0]['{}_raw_1d'.format(debug_sig_name)]]
        uncertaintylist=[records[0]['{}_uncertainty_raw_1d'.format(debug_sig_name)]]
        labels=['raw']
        for trial_fit in trial_fits:
            xlist.append(standard_x)
            ylist.append(records[0]['{}_{}'.format(debug_sig_name,trial_fit)])
            uncertaintylist.append(None)
            labels.append(trial_fit)
        xlist.append(standard_x)
        ylist.append(records[0]['zipfit_{}'.format(zipfit_pairs[debug_sig_name])])
        uncertaintylist.append(None)
        labels.append('zipfit_{}'.format(zipfit_pairs[debug_sig_name]))
        plot_comparison_over_time(xlist=xlist,
                                  ylist=ylist,
                                  time=records[0]['standard_time'],
                                  ylabel=debug_sig_name,
                                  xlabel='psi',
                                  uncertaintylist=uncertaintylist,
                                  labels=labels)

    if debug_sig_name in scalar_sig_names+efit_scalar_sig_names+nb_sig_names:
        plt.scatter(records[0]['{}_full'.format(debug_sig_name)]['times'][::100],
                    records[0]['{}_full'.format(debug_sig_name)]['data'][::100],
                    c='b',
                    label='original')
        plt.plot(records[0]['standard_time'],
                 records[0][debug_sig_name],
                 c='r',
                 label='interpolated')
        plt.legend()
        plt.xlabel('time (unit: {})'.format(records[0]['{}_full'.format(debug_sig_name)]['units']['times']))
        plt.ylabel('{} (unit: {})'.format(debug_sig_name, records[0]['{}_full'.format(debug_sig_name)]['units']['data']))
        plt.show()

    if debug_sig_name in efit_profile_sig_names:
        xlist=[standard_x]
        ylist=[records[0]['{}'.format(debug_sig_name)]]
        uncertaintylist=[None]
        labels=[debug_sig_name]
        plot_comparison_over_time(xlist=xlist,
                                  ylist=ylist,
                                  time=records[0]['standard_time'],
                                  ylabel=debug_sig_name,
                                  xlabel='psi',
                                  uncertaintylist=uncertaintylist,
                                  labels=labels)

