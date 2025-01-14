# Objects to make working with filters easier

from phoebe import u
from phoebe import c as const

import numpy as np
from spisea import synthetic

lambda_Ks = 2.18e-6 * u.m

class filter(object):
    def __init__(self):
        self.filter_name = 'filt'
        self.phoebe_ds_name = 'mod_lc_filt'
        self.phoebe_pb_name = 'tel_inst:filt'
        
        # Filter properties
        self.lambda_filt = 0.0 * u.m
        self.dlambda_filt = 0.0 * u.m
        
        self.filt_info = None
        
        self.flux_ref_filt = 0.0 * (u.erg / u.s) / (u.cm**2.)
        
        return
    
    def calc_isoc_filt_ext(self, isoc_Ks_ext, ext_alpha):
        isoc_filt_ext = isoc_Ks_ext *\
                        (lambda_Ks / self.lambda_filt)**ext_alpha
        
        return isoc_filt_ext
    
class naco_ks_filt(filter):
    def __init__(self):
        self.filter_name = 'naco,Ks'
        self.phoebe_ds_name = 'mod_lc_Ks'
        self.phoebe_pb_name = 'VLT_NACO:Ks'
        
        # Filter properties
        self.lambda_filt = 2.18e-6 * u.m
        self.dlambda_filt = 0.35e-6 * u.m
        
        self.filt_info = synthetic.get_filter_info(self.filter_name)
        
        self.flux_ref_filt = self.filt_info.flux0 * (u.erg / u.s) / (u.cm**2.)
        
        return

class nirc2_lp_filt(filter):
    def __init__(self):
        self.filter_name = 'nirc2,Lp'
        self.phoebe_ds_name = 'mod_lc_Lp'
        self.phoebe_pb_name = 'Keck_NIRC2:Lp'
        
        # Filter properties
        self.lambda_filt = 3.776e-6 * u.m
        self.dlambda_filt = 0.700e-6 * u.m
        
        self.filt_info = synthetic.get_filter_info(self.filter_name)
        
        self.flux_ref_filt = self.filt_info.flux0 * (u.erg / u.s) / (u.cm**2.)
        
        return

class nirc2_kp_filt(filter):
    def __init__(self):
        self.filter_name = 'nirc2,Kp'
        self.phoebe_ds_name = 'mod_lc_Kp'
        self.phoebe_pb_name = 'Keck_NIRC2:Kp'
        
        # Filter properties
        self.lambda_filt = 2.124e-6 * u.m
        self.dlambda_filt = 0.351e-6 * u.m
        
        self.filt_info = synthetic.get_filter_info(self.filter_name)
        
        self.flux_ref_filt = self.filt_info.flux0 * (u.erg / u.s) / (u.cm**2.)
        
        return

class nirc2_h_filt(filter):
    def __init__(self):
        self.filter_name = 'nirc2,H'
        self.phoebe_ds_name = 'mod_lc_H'
        self.phoebe_pb_name = 'Keck_NIRC2:H'
        
        # Filter properties
        self.lambda_filt = 1.633e-6 * u.m
        self.dlambda_filt = 0.296e-6 * u.m
        
        self.filt_info = synthetic.get_filter_info(self.filter_name)
        
        self.flux_ref_filt = self.filt_info.flux0 * (u.erg / u.s) / (u.cm**2.)
        
        return

class jwst_115w_filt(filter):
    def __init__(self):
        self.filter_name = 'jwst,F115W'
        self.phoebe_ds_name = 'mod_lc_115W'
        self.phoebe_pb_name = 'JWST_NIRCam:115W'
        
        # Filter properties
        self.lambda_filt = 1.154e-6 * u.m
        self.dlambda_filt = 0.225e-6 * u.m
        
        self.filt_info = synthetic.get_filter_info(self.filter_name)
        
        self.flux_ref_filt = self.filt_info.flux0 * (u.erg / u.s) / (u.cm**2.)
        
        return

class jwst_212n_filt(filter):
    def __init__(self):
        self.filter_name = 'jwst,F212N'
        self.phoebe_ds_name = 'mod_lc_212N'
        self.phoebe_pb_name = 'JWST_NIRCam:212N'
        
        # Filter properties
        self.lambda_filt = 2.120e-6 * u.m
        self.dlambda_filt = 0.027e-6 * u.m
        
        self.filt_info = synthetic.get_filter_info(self.filter_name)
        
        self.flux_ref_filt = self.filt_info.flux0 * (u.erg / u.s) / (u.cm**2.)
        
        return

class jwst_323n_filt(filter):
    def __init__(self):
        self.filter_name = 'jwst,F323N'
        self.phoebe_ds_name = 'mod_lc_323N'
        self.phoebe_pb_name = 'JWST_NIRCam:323N'
        
        # Filter properties
        self.lambda_filt = 3.237e-6 * u.m
        self.dlambda_filt = 0.038e-6 * u.m
        
        self.filt_info = synthetic.get_filter_info(self.filter_name)
        
        self.flux_ref_filt = self.filt_info.flux0 * (u.erg / u.s) / (u.cm**2.)
        
        return