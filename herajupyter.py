import capo, glob
from ipywidgets import interact
import numpy as np
import pylab as pl

class dataset(object):
    """ Objectify a day's worth of HERA/PAPER data """

    def __init__(self, selstr='zen.*.*.*.uvcRRE'):
        """ Default selstr enforces naming convention of zen.mjd.dd.pol.uvcRRE """

        properties = ['ants', 'times', 'pols', 'chans', 'intsperfile']
        
        self._files = glob.glob(selstr)

        for prop in properties:
            setattr(self, '_{0}'.format(prop), None)

        
    @property
    def times(self):
        if not self._times:
            self._times = list(set(['.'.join(ff.split('.')[1:3]) for ff in self._files]))

        return self._times

        
    @property
    def pols(self):
        if not self._pols:
            self._pols = list(set([ff.split('.')[3] for ff in self._files]))
        return self._pols
    
    
    @property
    def ants(self):
        if not self._ants:
            self.setdataproperties()

        return self._ants

    
    @property
    def chans(self):
        if not self._chans:
            self.setdataproperties()

        return self._chans

    
    @property
    def intsperfile(self):
        if not self._intsperfile:
            self.setdataproperties()
            
        return self._intsperfile
    

    @property
    def autokeys(self):
        return [(ant,ant) for ant in self.ants]
    
    
    def setdataproperties(self):
        """ Caches properties derived from data (which is slow) """

        info, data, flags = capo.miriad.read_files([self._files[0]], 'auto', 'xx')
        self._ants = sorted([key[0] for key in data.keys()])
        self._chans = range(data[data.keys()[0]]['xx'].shape[1])
        self._intsperfile = data[data.keys()[0]]['xx'].shape[0]

        
    def listfiles(self, time='', pol=''):
        """ Get file list filtered for given time and pol (strings) """

        assert isinstance(time, str) and isinstance(pol, str), 'time and pol should be strings'

        return [ff for ff in self._files if time in ff and pol in ff]

    
    def getautos(self, time='', pol='xx', decimate=1):
        """ Return autocorrs as numpy array after selecting for time and pol """
        
        assert ',' not in pol, 'Select a single pol product from (xx, xy, yx, yy).'

        filelist = self.listfiles(time, pol)
        
        if decimate > self.intsperfile:
            print('Currently only able to decimate up to {} integrations'.format(self.intsperfile))
            
        info, data, flags = capo.miriad.read_files(filelist, 'auto', pol, decimate)

        # make numpy array of shape (ntimes, nants, nchan)
        data = np.array([data[key][pol] for key in self.autokeys])
        return np.rollaxis(data, 1)


def exploredata(data, slider='chans', stack='ants'):
    """ Set up interactive plot for 3d data (ints, ants, chans). """
    
    axdict = {'ints': 0, 'ants': 1, 'chans': 2}
    assert slider in axdict.keys() and stack in axdict.keys(), 'slider or stack param not allowed'

    slax = axdict[slider]
    # need to account for axis shift after first 'take'
    stax = axdict[stack] if axdict[stack] <= slax else axdict[stack] - 1
    slmax = data.shape[axdict[slider]]
    stmax = data.shape[axdict[stack]]

    xaxis = [name for name in axdict.keys() if name != slider and name != stack][0]
    
    fcndict = {'Real': np.real, 'Imag': np.imag, 'Amp': np.abs, 'Phase': np.angle}

    @interact(sl=(0, slmax, 1), f=['Real', 'Imag', 'Amp', 'Phase'])
    def plotautos(sl, f):
        pl.figure(figsize=(15,8))
        pl.clf()
        pl.xlabel(xaxis)
        pl.ylabel(f)
        
        fcn =  fcndict[f]
        
        for st in range(stmax):
            pl.plot(fcn(data.take(sl, axis=slax).take(st, axis=stax)))
            
        print('Plotting {0} vs. {1}.'.format(f, xaxis))
        print('Slider for {0}. A line per {1}.'.format(slider, stack.rstrip('s')))
