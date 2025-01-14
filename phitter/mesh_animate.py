#!/usr/bin/env python

# Light curve calculation functions,
# for fitting with PHOEBE
# ---
# Abhimat Gautam

import phoebe
from phoebe import u
from phoebe import c as const

import numpy as np

from popstar import synthetic

import sys

from astropy.table import Table

import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
from matplotlib.ticker import MultipleLocator

# Filter properties
lambda_Ks = 2.18e-6 * u.m
dlambda_Ks = 0.35e-6 * u.m

lambda_Kp = 2.124e-6 * u.m
dlambda_Kp = 0.351e-6 * u.m

lambda_H = 1.633e-6 * u.m
dlambda_H = 0.296e-6 * u.m

# Reference fluxes, calculated with PopStar
## Vega magnitudes (m_Vega = 0.03)
ks_filt_info = synthetic.get_filter_info('naco,Ks')
kp_filt_info = synthetic.get_filter_info('nirc2,Kp')
h_filt_info = synthetic.get_filter_info('nirc2,H')

flux_ref_Ks = ks_filt_info.flux0 * (u.erg / u.s) / (u.cm**2.)
flux_ref_Kp = kp_filt_info.flux0 * (u.erg / u.s) / (u.cm**2.)
flux_ref_H = h_filt_info.flux0 * (u.erg / u.s) / (u.cm**2.)

# Stellar Parameters
# stellar_params = (mass, rad, teff, mag_Kp, mag_H, pblum_Kp, pblum_H)

def single_star_mesh(stellar_params,
        use_blackbody_atm=False,
        num_triangles=1500):
    # Read in the stellar parameters of the current star
    (star_mass, star_rad, star_teff, star_logg,
     star_mag_Kp, star_mag_H, star_pblum_Kp, star_pblum_H) = stellar_params
    
    err_out = np.array([-1.])

    # Set up a single star model
    sing_star = phoebe.default_star()
    
    # Light curve dataset
    if use_blackbody_atm:
        sing_star.add_dataset(phoebe.dataset.lc, times=[0], dataset='mod_lc_Kp', passband='Keck_NIRC2:Kp', ld_func='linear', ld_coeffs=[0.0])
        sing_star.add_dataset(phoebe.dataset.lc, times=[0], dataset='mod_lc_H', passband='Keck_NIRC2:H', ld_func='linear', ld_coeffs=[0.0])
        # sing_star.add_dataset(phoebe.dataset.lc, times=[0], dataset='mod_lc_V', passband='Johnson:V', ld_func='linear', ld_coeffs=[0.0])
    else:
        sing_star.add_dataset(phoebe.dataset.lc, times=[0], dataset='mod_lc_Kp', passband='Keck_NIRC2:Kp')
        sing_star.add_dataset(phoebe.dataset.lc, times=[0], dataset='mod_lc_H', passband='Keck_NIRC2:H')
        # sing_star.add_dataset(phoebe.dataset.lc, times=[0], dataset='mod_lc_V', passband='Johnson:V')
    
    # Set up compute
    if use_blackbody_atm:
        sing_star.add_compute('phoebe', compute='detailed', distortion_method='sphere', irrad_method='none', atm='blackbody')
    else:
        sing_star.add_compute('phoebe', compute='detailed', distortion_method='sphere', irrad_method='none')
    
    # Set a default distance
    sing_star.set_value('distance', 10 * u.pc)
    
    # Set the passband luminosities
    sing_star.set_value('pblum@mod_lc_Kp', star_pblum_Kp)
    sing_star.set_value('pblum@mod_lc_H', star_pblum_H)
    
    # Set the stellar parameters
    sing_star.set_value('teff@component', star_teff)
    sing_star.set_value('requiv@component', star_rad)
    
    # Set the number of triangles in the mesh
    sing_star.set_value('ntriangles@detailed@compute', num_triangles)
    
    # Run compute
    try:
        sing_star.run_compute(compute='detailed', model='run',
                              progressbar=False)
    except: # Catch errors during computation (probably shouldn't happen during individual star computation)
        print("Error during primary ind. star compute: {0}".format(sys.exc_info()[0]))
        return (err_out, err_out)
    
    # Retrieve computed fluxes from phoebe
    sing_star_fluxes_Kp = np.array(sing_star['fluxes@lc@mod_lc_Kp@model'].value) * u.W / (u.m**2)
    sing_star_mags_Kp = -2.5 * np.log10(sing_star_fluxes_Kp / flux_ref_Kp) + 0.03
    
    sing_star_fluxes_H = np.array(sing_star['fluxes@lc@mod_lc_H@model'].value) * u.W / (u.m**2)
    sing_star_mags_H = -2.5 * np.log10(sing_star_fluxes_H / flux_ref_H) + 0.03
        
    return (sing_star_mags_Kp, sing_star_mags_H)

def binary_star_mesh(star1_params, star2_params, binary_params, observation_times,
        use_blackbody_atm=False,
        make_mesh_plots=True,
        mesh_temp=False, mesh_temp_cmap=None,
        plot_name=None,
        print_diagnostics=False, par_compute=False, num_par_processes=8,
        num_triangles=1500):
    """Compute the light curve for a binary system
    
    Keyword arguments:
    star1_params -- Tuple of parameters for the primary star
    star2_params -- Tuple of parameters for the secondary star
    binary_params -- Tuple of parameters for the binary system configuration
    observation_times -- Tuple of observation times,
        with numpy array of MJDs in each band
        (kp_MJDs, h_MJDs, mesh_MJDs) = observation_times
    use_blackbody_atm -- Use blackbody atmosphere
        instead of default Castelli & Kurucz (default False)
    make_mesh_plots -- Make a mesh plot of the binary system (default True)
    plot_name
    print_diagnostics
    par_compute
    num_par_processes
    """
    
    if par_compute:
        # TODO: Need to implement parallelization correctly
        phoebe.mpi_on(nprocs=num_par_processes)
    else:
        phoebe.mpi_off()
    
    # Read in the stellar parameters of the binary components
    (star1_mass, star1_rad, star1_teff, star1_logg,
     star1_mag_Kp, star1_mag_H,
     star1_pblum_Kp, star1_pblum_H) = star1_params
    (star2_mass, star2_rad, star2_teff, star2_logg,
     star2_mag_Kp, star2_mag_H,
     star2_pblum_Kp, star2_pblum_H) = star2_params
    
    # Read in the parameters of the binary system
    (binary_period, binary_ecc, binary_inc, t0) = binary_params
    
    err_out = (np.array([-1.]), np.array([-1.]))
    
    # Check for high temp ck2004 atmosphere limits
    if not use_blackbody_atm:
        # log g = 3.5, high temp bounds (above 31e3 K)
        if star1_teff > (31000 * u.K) and (4.0 > star1_logg > 3.5):
            star1_teff_round = 30995.0 * u.K
            
            if print_diagnostics:
                print('Star 1 out of C&K 2004 grid')
                print('star1_logg = {0:.4f}'.format(star1_logg))
                print('Rounding down star1_teff')
                print('{0:.4f} -> {1:.4f}'.format(star1_teff, star1_teff_round))
            
            star1_teff = star1_teff_round
        if star2_teff > (31000 * u.K) and (4.0 > star2_logg > 3.5):
            star2_teff_round = 30995.0 * u.K
            
            if print_diagnostics:
                print('Star 2 out of C&K 2004 grid')
                print('star2_logg = {0:.4f}'.format(star2_logg))
                print('Rounding down star2_teff')
                print('{0:.4f} -> {1:.4f}'.format(star2_teff, star2_teff_round))
            
            star2_teff = star2_teff_round
        
        # log g = 4.0, high temp bounds (above 40e3 K)
        if star1_teff > (40000 * u.K) and (4.5 > star1_logg > 4.0):
            star1_teff_round = 39995.0 * u.K
            
            print('Star 1 out of C&K 2004 grid')
            print('star1_logg = {0:.4f}'.format(star1_logg))
            print('Rounding down star1_teff')
            print('{0:.4f} -> {1:.4f}'.format(star1_teff, star1_teff_round))
            
            star1_teff = star1_teff_round
        if star2_teff > (40000 * u.K) and (4.0 > star2_logg > 3.50):
            star2_teff_round = 39995.0 * u.K
            
            print('Star 2 out of C&K 2004 grid')
            print('star2_logg = {0:.4f}'.format(star2_logg))
            print('Rounding down star2_teff')
            print('{0:.4f} -> {1:.4f}'.format(star2_teff, star2_teff_round))
            
            star2_teff = star2_teff_round
    
    # Set up binary model
    b = phoebe.default_binary()
    
    ## Set a default distance
    b.set_value('distance', 10 * u.pc)
    
    ## Set period, semimajor axis, and mass ratio (q)
    binary_sma = ((binary_period**2. * const.G * (star1_mass + star2_mass)) / (4. * np.pi**2.))**(1./3.)
    
    binary_q = star2_mass / star1_mass
    
    if print_diagnostics:
        print('\nBinary orbit checks')
        print('Binary SMA: {0}'.format(binary_sma.to(u.AU)))
        print('Binary Mass Ratio (q): {0}'.format(binary_q))
    
    b.set_value('period@orbit', binary_period)
    b.set_value('sma@binary@component', binary_sma)
    b.set_value('q@binary@component', binary_q)
    
    ## Inclination
    b.set_value('incl@orbit', binary_inc)
    
    # Check for overflow
    ## Variables to help store the non-detached binary cases
    star1_semidetached = False
    star2_semidetached = False
    
    star1_overflow = False
    star2_overflow = False
    
    ## Get the max radii for both component stars
    star1_rad_max = b.get_value('requiv_max@primary@component') * u.solRad
    star2_rad_max = b.get_value('requiv_max@secondary@component') * u.solRad
    
    ## Check for semidetached cases
    if print_diagnostics:
        print('\nSemidetached checks')
        print('Star 1: {0}'.format(np.abs((star1_rad - star1_rad_max) / star1_rad_max)))
        print('Star 2: {0}'.format(np.abs((star2_rad - star2_rad_max) / star2_rad_max)))
    
    semidet_cut = 0.001   # (within 0.1% of max radii)
    semidet_cut = 0.015   # (within 1.5% of max radii)
    
    if np.abs((star1_rad - star1_rad_max) / star1_rad_max) < semidet_cut:
        star1_semidetached = True
    if np.abs((star2_rad - star2_rad_max) / star2_rad_max) < semidet_cut:
        star2_semidetached = True
    
    ## Check for overflow
    if (star1_rad > star1_rad_max) and not star1_semidetached:
        star1_overflow = True
    
    if (star2_rad > star2_rad_max) and not star2_semidetached:
        star2_overflow = True
    
    
    
    ### Check for if both stars are overflowing; which star overflows more?
    ### Choose that star to be overflowing more
    if star1_overflow and star2_overflow:
        if (star1_rad - star1_rad_max) >= (star2_rad - star2_rad_max):
            star2_overflow = False
        else:
            star1_overflow = False
    
    
    if print_diagnostics:
        print('\nOverflow Checks')
        print('Star 1 Semidetached: {0}'.format(star1_semidetached))
        print('Star 2 Semidetached: {0}'.format(star2_semidetached))
        print('Star 1 Overflow: {0}'.format(star1_overflow))
        print('Star 2 Overflow: {0}'.format(star2_overflow))
    
    # If star 2 is overflowing, have to re set up model:
    # Calling this same binary_star_lc function again,
    # with star 2 as primary and star 1 as secondary.
    # Change t0 = t0 - per/2 to make sure phase is correct,
    # wrt stars 1 and 2 being in same respective position
    if star2_overflow and not star1_overflow:
        redo_binary_params = (binary_period, binary_ecc, binary_inc,
                              t0 - (binary_period.to(u.d).value/2.))
        
        return binary_star_lc(star2_params, star1_params,
                    redo_binary_params,
                    observation_times,
                    use_blackbody_atm=use_blackbody_atm,
                    make_mesh_plots=make_mesh_plots,
                    mesh_temp=mesh_temp, mesh_temp_cmap=mesh_temp_cmap,
                    plot_name=plot_name,
                    print_diagnostics=print_diagnostics,
                    par_compute=par_compute, num_par_processes=num_par_processes,
                    num_triangles=num_triangles)
    
    ## If none of these overflow cases, set variable to store if binary is detached
    binary_detached = (not star1_semidetached) and \
                      (not star2_semidetached) and \
                      (not star1_overflow) and \
                      (not star2_overflow)
    
    ### Set non-zero eccentricity only if binary is detached
    if binary_detached:
        b.set_value('ecc@binary@component', binary_ecc)
    else:
        b.set_value('ecc@binary@component', 0.)
    
    ## Change set up for contact or semidetached cases
    if star1_overflow or star2_overflow:
        b = phoebe.default_binary(contact_binary=True)
        
        ### Reset all necessary binary properties for contact system
        b.set_value('distance', 10 * u.pc)
        
        b.set_value('period@orbit', binary_period)
        b.set_value('sma@binary@component', binary_sma)
        b.set_value('q@binary@component', binary_q)
        b.set_value('incl@orbit', binary_inc)
    
    if star1_semidetached and not star2_overflow:
        b.add_constraint('semidetached', 'primary')
    if star2_semidetached and not star1_overflow:
        b.add_constraint('semidetached', 'secondary')
    
    # Set up compute
    if use_blackbody_atm:
        b.add_compute('phoebe', compute='detailed',
                      irrad_method='wilson', atm='blackbody')
    else:
        b.add_compute('phoebe', compute='detailed', irrad_method='wilson')
    
    # Set the parameters of the component stars of the system
    ## Primary
    b.set_value('teff@primary@component', star1_teff)
    # b.set_value('logg@primary@component', star1_logg)
    if (not star1_semidetached) and (not star2_overflow):
        b.set_value('requiv@primary@component', star1_rad)
    
    ## Secondary
    b.set_value('teff@secondary@component', star2_teff)
    # b.set_value('logg@secondary@component', star2_logg)
    if (not star2_semidetached) and (not star1_overflow) and (not star2_overflow):
        try:
            b.set_value('requiv@secondary@component', star2_rad)
        except:
            print('\nOverflow Checks')
            print('Star 1 Semidetached: {0}'.format(star1_semidetached))
            print('Star 2 Semidetached: {0}'.format(star2_semidetached))
            print('Star 1 Overflow: {0}'.format(star1_overflow))
            print('Star 2 Overflow: {0}'.format(star2_overflow))
            
            print("Cannot set secondary radius: {0}".format(sys.exc_info()[0]))
            
            return err_out
    
    
    # Set the number of triangles in the mesh
    # Detached stars
    if len(b.filter('ntriangles@primary@detailed@compute')) == 1: 
        b.set_value('ntriangles@primary@detailed@compute', num_triangles)
        
    if len(b.filter('ntriangles@secondary@detailed@compute')) == 1: 
        b.set_value('ntriangles@secondary@detailed@compute', num_triangles)
    
    # Contact envelope
    if len(b.filter('ntriangles@contact_envelope@detailed@compute')) == 1:
       if print_diagnostics:
           print('Setting number of triangles for contact envelope')
       b.set_value('ntriangles@contact_envelope@detailed@compute',
                   num_triangles * 2.)
    
    # Phase the observation times
    ## Read in observation times
    (kp_MJDs, h_MJDs, mesh_MJDs) = observation_times
    
    ## Phase the observation times
    kp_phased_days = ((kp_MJDs - t0) % binary_period.to(u.d).value) / binary_period.to(u.d).value
    h_phased_days = ((h_MJDs - t0) % binary_period.to(u.d).value) / binary_period.to(u.d).value
    mesh_phased_days = ((mesh_MJDs - t0) % binary_period.to(u.d).value) / binary_period.to(u.d).value
    
    # Add light curve datasets
    ## Kp
    kp_phases_sorted_inds = np.argsort(kp_phased_days)
    
    kp_model_times = (kp_phased_days) * binary_period.to(u.d).value
    kp_model_times = kp_model_times[kp_phases_sorted_inds]
    
    # b.add_dataset(phoebe.dataset.lc, time=kp_model_times,
    #               dataset='mod_lc_Kp', passband='Keck_NIRC2:Kp')
    if use_blackbody_atm:
        b.add_dataset(phoebe.dataset.lc, time=kp_model_times,
                      dataset='mod_lc_Kp', passband='Keck_NIRC2:Kp')
        b.set_value('ld_mode@primary@mod_lc_Kp', 'manual')
        b.set_value('ld_mode@secondary@mod_lc_Kp', 'manual')
        b.set_value('ld_func@primary@mod_lc_Kp', 'logarithmic')
        b.set_value('ld_func@secondary@mod_lc_Kp', 'logarithmic')
    else:
        b.add_dataset(phoebe.dataset.lc, time=kp_model_times,
                      dataset='mod_lc_Kp', passband='Keck_NIRC2:Kp')
    
    ## H
    h_phases_sorted_inds = np.argsort(h_phased_days)
    
    h_model_times = (h_phased_days) * binary_period.to(u.d).value
    h_model_times = h_model_times[h_phases_sorted_inds]
    
    # b.add_dataset(phoebe.dataset.lc, times=h_model_times,
    #               dataset='mod_lc_H', passband='Keck_NIRC2:H')
    if use_blackbody_atm:
        b.add_dataset(phoebe.dataset.lc, times=h_model_times,
                      dataset='mod_lc_H', passband='Keck_NIRC2:H')
        b.set_value('ld_mode@primary@mod_lc_H', 'manual')
        b.set_value('ld_mode@secondary@mod_lc_H', 'manual')
        b.set_value('ld_func@primary@mod_lc_H', 'logarithmic')
        b.set_value('ld_func@secondary@mod_lc_H', 'logarithmic')
    else:
        b.add_dataset(phoebe.dataset.lc, times=h_model_times,
                      dataset='mod_lc_H', passband='Keck_NIRC2:H')
    
    # Add mesh dataset if making mesh plot
    mesh_phases_sorted_inds = np.argsort(mesh_phased_days)
    
    mesh_model_times = (mesh_phased_days) * binary_period.to(u.d).value
    mesh_model_times = mesh_model_times[mesh_phases_sorted_inds]
    
    if make_mesh_plots:
        b.add_dataset('mesh', times=mesh_model_times,
                      dataset='mod_mesh')
        
        if mesh_temp:
            b['columns@mesh'] = ['teffs', 'loggs']
    
    # Set the passband luminosities for the stars
    b.set_value('pblum_mode@mod_lc_Kp', 'decoupled')
    b.set_value('pblum_mode@mod_lc_H', 'decoupled')
    
    b.set_value('pblum@primary@mod_lc_Kp', star1_pblum_Kp)
    b.set_value('pblum@primary@mod_lc_H', star1_pblum_H)
    
    b.set_value('pblum@secondary@mod_lc_Kp', star2_pblum_Kp)
    b.set_value('pblum@secondary@mod_lc_H', star2_pblum_H)
    
    # Run compute
    # if print_diagnostics:
    #     print("Trying inital compute run")
    #     b.run_compute(compute='detailed', model='run',
    #                   progressbar=False)

    try:
        b.run_compute(compute='detailed', model='run',
                      progressbar=False)
    except:
        if print_diagnostics:
            print("Error during primary binary compute: {0}".format(sys.exc_info()[0]))
        return err_out
    
    
    # Save out mesh plot
    if make_mesh_plots:
        ## Plot Nerdery
        plt.rc('font', family='serif')
        plt.rc('font', serif='Computer Modern Roman')
        plt.rc('text', usetex=True)
        plt.rc('text.latex', preamble=r"\usepackage{gensymb}")

        plt.rc('xtick', direction = 'in')
        plt.rc('ytick', direction = 'in')
        # plt.rc('xtick', top = True)
        # plt.rc('ytick', right = True)
        
        suffix_str = ''
        if plot_name is not None:
            suffix_str = '_' + plot_name
        
        ## Mesh plot
        mesh_plot_out = []
        
        if mesh_temp:
            b['mod_mesh@model'].plot(
                fc='teffs',
                fcmap=mesh_temp_cmap,
                ec='face',
                animate=True,
                save='./binary_mesh{0}.gif'.format(suffix_str),
                save_kwargs={'writer': 'imagemagick'})
            for (mesh_model_time, mesh_index) in zip(mesh_model_times, range(len(mesh_model_times))):
                plt.clf()
                new_fig = plt.figure()
                (mesh_af_fig, mesh_plt_fig) = b['mod_mesh@model'].plot(
                    fig=new_fig,
                    time=mesh_model_time,
                    fc='teffs',
                    fcmap=mesh_temp_cmap,
                    ec='face',
                    save='./binary_mesh_{0}.pdf'.format(mesh_index))
                mesh_plot_out.append(mesh_plt_fig)
                plt.close(new_fig)
        else:
            b['mod_mesh@model'].plot(
                animate=True,
                save='./binary_mesh{0}.gif'.format(suffix_str),
                save_kwargs={'writer': 'imagemagick'})
            for mesh_model_time in mesh_model_times:
                mesh_plot_out.append(b['mod_mesh@model'].plot(
                    time=mesh_model_time,
                    save='./binary_mesh.pdf'.format(suffix_str)))
    
    
    # Get fluxes
    ## Kp
    model_fluxes_Kp = np.array(b['fluxes@lc@mod_lc_Kp@model'].value) * u.W / (u.m**2.)
    model_mags_Kp = -2.5 * np.log10(model_fluxes_Kp / flux_ref_Kp) + 0.03
    
    ## H
    model_fluxes_H = np.array(b['fluxes@lc@mod_lc_H@model'].value) * u.W / (u.m**2.)
    model_mags_H = -2.5 * np.log10(model_fluxes_H / flux_ref_H) + 0.03
    
    if print_diagnostics:
        print('\nFlux Checks')
        print('Fluxes, Kp: {0}'.format(model_fluxes_Kp))
        print('Mags, Kp: {0}'.format(model_mags_Kp))
        print('Fluxes, H: {0}'.format(model_fluxes_H))
        print('Mags, H: {0}'.format(model_mags_H))
    
    if make_mesh_plots:
        return (model_mags_Kp, model_mags_H, mesh_plot_out)
    else:
        return (model_mags_Kp, model_mags_H)
    
def phased_obs(observation_times, binary_period, t0):
    # Phase the observation times
    ## Read in observation times
    (kp_MJDs, h_MJDs) = observation_times
    
    ## Phase the observation times
    kp_phased_days = ((kp_MJDs - t0) % binary_period.to(u.d).value) / binary_period.to(u.d).value
    h_phased_days = ((h_MJDs - t0) % binary_period.to(u.d).value) / binary_period.to(u.d).value
    
    ## Kp
    kp_phases_sorted_inds = np.argsort(kp_phased_days)
    
    kp_model_times = (kp_phased_days) * binary_period.to(u.d).value
    kp_model_times = kp_model_times[kp_phases_sorted_inds]
    
    ## H
    h_phases_sorted_inds = np.argsort(h_phased_days)
    
    h_model_times = (h_phased_days) * binary_period.to(u.d).value
    h_model_times = h_model_times[h_phases_sorted_inds]
    
    return ((kp_phased_days, kp_phases_sorted_inds, kp_model_times),
            (h_phased_days, h_phases_sorted_inds, h_model_times))


def dist_ext_mag_calc(input_mags, target_dist, Kp_ext, H_ext):
    (mags_Kp, mags_H) = input_mags
    
    # App mag at target distance (default system dist = 10 pc)
    mags_Kp = mags_Kp + 5. * np.log10(target_dist / (10. * u.pc))
    mags_H = mags_H + 5. * np.log10(target_dist / (10. * u.pc))
    
    # Add extinction
    mags_Kp = mags_Kp + Kp_ext
    mags_H = mags_H + H_ext
    
    # Return mags at target distance and extinction
    return (mags_Kp, mags_H)
    

def flux_adj(mags_pri, mags_ref_pri, mags_sec, mags_ref_sec, mags_bin):
    """Perform flux adjustment for binary magnitudes
    * Uses calculated and reference single star magnitudes for binary components
    * Derives adjustment to binary magnitude based on the discrepancy
    * Applies correction to the calculated binary magnitudes
    
    Keyword arguments:
    mags_pri -- Model calculated magnitudes (Kp, H) of primary
    mags_ref_pri -- Reference magnitudes (Kp, H) of primary
    mags_sec -- Model calculated magnitudes (Kp, H) of secondary
    mags_ref_sec -- Reference magnitudes (Kp, H) of secondary
    mags_bin -- Model calculated magnitudes ([Kp], [H]) of the binary system
    """
    
    # Properly expand and extract the input magnitudes
    (mag_pri_Kp, mag_pri_H) = mags_pri
    (mag_ref_pri_Kp, mag_ref_pri_H) = mags_ref_pri
    
    (mag_sec_Kp, mag_sec_H) = mags_sec
    (mag_ref_sec_Kp, mag_ref_sec_H) = mags_ref_sec
    
    (mags_bin_Kp, mags_bin_H) = mags_bin
    
    # Calculate flux adjustment for each component star
    flux_adj_star_pri_Kp = (10.**((mag_pri_Kp[0] - mag_ref_pri_Kp)/2.5))
    flux_adj_star_pri_H = (10.**((mag_pri_H[0] - mag_ref_pri_H)/2.5))
    
    flux_adj_star_sec_Kp = (10.**((mag_sec_Kp[0] - mag_ref_sec_Kp)/2.5))
    flux_adj_star_sec_H = (10.**((mag_sec_H[0] - mag_ref_sec_H)/2.5))
    
    # Calculate total flux adjustment for the binary system
    flux_adj_bin_Kp = ((10.**(mag_ref_pri_Kp / -2.5)) + (10.**(mag_ref_sec_Kp / -2.5))) / ((10.**(mag_pri_Kp[0] / -2.5)) + (10.**(mag_sec_Kp[0] / -2.5)))
    flux_adj_bin_H = ((10.**(mag_ref_pri_H / -2.5)) + (10.**(mag_ref_sec_H / -2.5))) / ((10.**(mag_pri_H[0] / -2.5)) + (10.**(mag_sec_H[0] / -2.5)))
    
    
    # Apply flux adjustment to the input binary magnitudes
    ## Convert magnitudes back into flux space
    fluxes_bin_Kp = flux_ref_Kp * (10.**((mags_bin_Kp - 0.03)/ -2.5))
    fluxes_bin_H = flux_ref_H * (10.**((mags_bin_H - 0.03)/ -2.5))
    
    ## Apply flux adjustment, derived from the single stars
    fluxes_bin_Kp = fluxes_bin_Kp * flux_adj_bin_Kp
    fluxes_bin_H = fluxes_bin_H * flux_adj_bin_H
    
    ## Convert to magnitudes and return
    adj_mags_bin_Kp = -2.5 * np.log10(fluxes_bin_Kp / flux_ref_Kp) + 0.03
    adj_mags_bin_H = -2.5 * np.log10(fluxes_bin_H / flux_ref_H) + 0.03
    
    return (adj_mags_bin_Kp, adj_mags_bin_H)


def binary_mesh_calc(star1_params_lcfit, star2_params_lcfit,
                     binary_params,
                     observation_times,
                     isoc_Ks_ext, Kp_ext, H_ext, ext_alpha,
                     isoc_dist, bin_dist,
                     use_blackbody_atm=False,
                     make_mesh_plots=False, mesh_temp=False, mesh_temp_cmap=None,
                     plot_name=None,
                     num_triangles=1500,
                     print_diagnostics=False):
    
    # Extinction law (using Nogueras-Lara+ 2018)
    ext_alpha = 2.30
    
    # Calculate extinctions implied by isochrone extinction
    isoc_Kp_ext = isoc_Ks_ext * (lambda_Ks / lambda_Kp)**ext_alpha
    isoc_H_ext = isoc_Ks_ext * (lambda_Ks / lambda_H)**ext_alpha
    
    # Calculate extinction adjustments
    Kp_ext_adj = (Kp_ext - isoc_Kp_ext)
    H_ext_adj = (H_ext - isoc_H_ext)
    
    # Calculate distance modulus adjustments
    dist_mod_mag_adj = 5. * np.log10(bin_dist / (isoc_dist.to(u.pc)).value)
    
    # Extract stellar parameters from input
    (star1_mass, star1_rad, star1_teff, star1_logg,
     star1_mag_Kp, star1_mag_H, star1_pblum_Kp, star1_pblum_H) = star1_params_lcfit
    (star2_mass, star2_rad, star2_teff, star2_logg,
     star2_mag_Kp, star2_mag_H, star2_pblum_Kp, star2_pblum_H) = star2_params_lcfit
    
    
    # Run binary star model to get binary mags
    binary_star_lc_out = binary_star_mesh(
        star1_params_lcfit,
        star2_params_lcfit,
        binary_params,
        observation_times,
        use_blackbody_atm=use_blackbody_atm,
        make_mesh_plots=make_mesh_plots,
        mesh_temp=mesh_temp,
        mesh_temp_cmap=mesh_temp_cmap,
        plot_name=plot_name,
        num_triangles=num_triangles,
        print_diagnostics=print_diagnostics)
    
    print(binary_star_lc_out)
    
    if make_mesh_plots:
        (binary_mags_Kp, binary_mags_H, mesh_plot_out) = binary_star_lc_out
    else:
        (binary_mags_Kp, binary_mags_H) = binary_star_lc_out
    
    if (binary_mags_Kp[0] == -1.) or (binary_mags_H[0] == -1.):
        return -np.inf
    
    ## Apply distance modulus and isoc. extinction to binary magnitudes
    (binary_mags_Kp, binary_mags_H) = dist_ext_mag_calc(
                                          (binary_mags_Kp, binary_mags_H),
                                          isoc_dist,
                                          isoc_Kp_ext, isoc_H_ext)
    
    # Apply the extinction difference between model and the isochrone values
    binary_mags_Kp += Kp_ext_adj
    binary_mags_H += H_ext_adj
    
    # Apply the distance modulus for difference between isoc. distance and bin. distance
    # (Same for each filter)
    binary_mags_Kp += dist_mod_mag_adj
    binary_mags_H += dist_mod_mag_adj
    
    # Return final light curve
    if make_mesh_plots:
        return (binary_mags_Kp, binary_mags_H, mesh_plot_out)
    else:
        return (binary_mags_Kp, binary_mags_H)