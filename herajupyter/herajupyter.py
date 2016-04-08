import capo, glob
from ipywidgets import interact
import numpy as np
import pylab as pl
import matplotlib.pyplot as plt
import os.path
from mpldatacursor import datacursor


class dataset(object):
    """ Objectify a day's worth of HERA/PAPER data """

    def __init__(self, visstr='zen.*.*.*.uvcRRE'):
        """ Default selstr enforces naming convention of zen.mjd.dd.pol.uvcRRE """

        __properties__ = ['ants', 'times', 'pols', 'chans', 'intsperfile']

        self.visstr = visstr
        self.npzstr = visstr.rstrip('.uvcRRE') + '.npz'
        self.workdir = os.path.abspath(os.path.dirname(self.visstr))

        for prop in __properties__:
            setattr(self, '_{0}'.format(prop), None)

        self._visfiles = glob.glob(visstr)

        if self._visfiles:
            print('Found {0} files with times from {1} to {2}'.format(len(self._visfiles), self.times[0], self.times[-1]))
        else:
            print('No files found.')

        
    @property
    def times(self):
        if not self._times:
            self._times = list(sorted(set(['.'.join(ff.split('.')[1:3]) for ff in self._visfiles])))

        return self._times

        
    @property
    def pols(self):
        if not self._pols:
            self._pols = list(set([ff.split('.')[3] for ff in self._visfiles]))
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

        info, data, flags = capo.miriad.read_files([self._visfiles[0]], 'auto', 'xx')
        self._ants = sorted([key[0] for key in data.keys()])
        self._chans = range(data[data.keys()[0]]['xx'].shape[1])
        self._intsperfile = data[data.keys()[0]]['xx'].shape[0]

        
    def listvisfiles(self, time='', pol=''):
        """ Get file list filtered for given time and pol (strings) """

        assert isinstance(time, str) and isinstance(pol, str), 'time and pol should be strings'

        return [ff for ff in self._visfiles if time in ff and pol in ff]


    def listnpzfiles(self, time='', pol=''):
        """ Get file list filtered for given time and pol (strings) """

        assert isinstance(time, str) and isinstance(pol, str), 'time and pol should be strings'

        return [ff for ff in glob.glob(self.npzstr) if time in ff and pol in ff]

    
    def getautos(self, time='', pol='xx', decimate=1):
        """ Return autocorrs as numpy array after selecting for time and pol """
        
        assert ',' not in pol, 'Select a single pol product from (xx, xy, yx, yy).'

        filelist = self.listvisfiles(time, pol)
        
        if decimate > self.intsperfile:
            print('Currently only able to decimate up to {} integrations'.format(self.intsperfile))
            
        info, data, flags = capo.miriad.read_files(filelist, 'auto', pol, decimate)

        # make numpy array of shape (ntimes, nants, nchan)
        data = np.array([data[key][pol] for key in self.autokeys])
        return np.rollaxis(data, 1)


def exploredata1d(data, slider='chans', stack='ants'):
    """ Set up interactive 1d (line) plotting for vis data of dimension (ints, ants, chans). """
    
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
            pl.plot(fcn(data.take(sl, axis=slax).take(st, axis=stax)), label='{0} {1}'.format(stack.rstrip('s'), st))
            
        print('Plotting {0} vs. {1}.'.format(f, xaxis))
        print('Slider for {0}. A line per {1}.'.format(slider, stack.rstrip('s')))
        print('Click on a line to see {0} number'.format(stack.rstrip('s')))
    datacursor(formatter='{label}'.format)


def exploredatawf(data):
    """ Set up interactive waterfall plot from vis data of dimension (ints, ants, chans). """
    
    fcndict = {'Real': np.real, 'Imag': np.imag, 'Amp': np.abs, 'Phase': np.angle}
    nints, nants, nchans = data.shape

    @interact(ant=(0, nants, 1), f=['Real', 'Imag', 'Amp', 'Phase'])
    def plotautos(ant, f):
        pl.figure(figsize=(15,8))
        pl.clf()
        pl.xlabel('Chans')
        pl.ylabel('Ints')
        
        fcn =  fcndict[f]
        
        pl.imshow(fcn(data[:,ant,:]), interpolation='nearest', origin='lower', aspect='equal')

        print('Plotting ints vs chans.')
        print('Slider for ants.')
#        print('Click on a line to see {0} number'.format(axdict[stack].rstrip('s')))


def omni_check(npzfiles, pol):
    """ Copy of omni_check to function with notebook interaction

    npzfiles is a list of npz files
    optional pol parameter is a string with comma-delimited pol
    interact can choose 'chisq', 'gains', or 'chisqant'.
    """

#    set up data structures
    if not pol:
        pol = npzfiles[0].split('.')[3] #XXX hard-coded for *pol.npz files

    chisqs = []
    gains = {} #or chisqant values, depending on option

    for i,filename in enumerate(npzfiles):
        print('Reading {0}'.format(filename))
        file = np.load(filename)

        # reads *pol.npz files
        try: 
            chisq = file['chisq '+str(pol)]
        except: #reads .npz files
            chisq = file['chisq']
        for t in range(len(chisq)):
            chisqs.append(chisq[t])

        for key in file.keys(): #loop over antennas
            if key[0] != '<' and key[0] != '(' and key[0].isalpha() != True:
                gain = file[key]
                antnum = key[:-1]
                try: gains[antnum].append(gain)
                except: gains[antnum] = [gain]
                vmax=1.5
            if key[0] == 'c' and len(key) > 5: #if plotting chisq per ant
                gain = file[key]
                antnum = key.split('chisq')[1][:-1]
                try: gains[antnum].append(gain)
                except: gains[antnum] = [gain]
                vmax=2
        for key in gains.keys():
            gains[key] = np.vstack(np.abs(gains[key])) #cool thing to stack 2D arrays that only match in 1 dimension
            mk = np.ma.masked_where(gains[key] == 1,gains[key]).mask #flags
            gains[key] = np.ma.masked_array(gains[key],mask=mk) #masked array

    @interact(type=['gains', 'chisq', 'chisqant'])
    def omni_check_plot(type):
        ### Plot ChiSq ####
        if type ==  'chisq':
            cs = np.array(chisqs)
            plt.imshow(np.log(cs),aspect='auto',interpolation='nearest',vmax=7,vmin=-6)
            plt.xlabel('Freq Channel',fontsize=10)
            plt.ylabel('Time',fontsize=10)
            plt.tick_params(axis='both',which='major',labelsize=8)
            plt.title('Omnical ChiSquare',fontsize=12)
            plt.colorbar()
            plt.show()

        ### Plot Gains ###
        elif type == 'gains' or type == 'chisqant':
            subplotnum = 1
            plotnum = 1
            plt.figure(plotnum,figsize=(10,10))
            for ant in gains.keys(): #loop over antennas
                if subplotnum == 26:
                #break #only generate one page of plots (faster for testing) 
                    plotnum += 1
                    plt.figure(plotnum,figsize=(10,10))
                    subplotnum = 1
                plt.subplot(5,5,subplotnum)
                plt.imshow(gains[ant],vmax=vmax,aspect='auto',interpolation='nearest')
                plt.title(ant,fontsize=10)
                plt.tick_params(axis='both',which='major',labelsize=6)
                plt.tight_layout()
                subplotnum += 1
            plt.show()


