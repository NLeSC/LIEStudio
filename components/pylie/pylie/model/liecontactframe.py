import logging
import numpy
import itertools
import re
import copy

from   pandas                   import DataFrame, Series, concat, isnull
from   scipy.spatial.distance   import pdist, squareform

from   pylie.model.liebase      import LIEDataFrameBase
from   pylie.model.liedataframe import LIEDataFrame
from   pylie.model.lieseries    import LIESeries
from   pylie.methods.fileio     import PDBParser, MOL2Parser, _open_anything
from   pylie.methods.data       import METALS, STRUCTURE_DATA_INFO
from   pylie.methods.geometry   import *

logger = logging.getLogger('pylie')

DEFAULT_CONTACT_COLUMN_NAMES = {'atnum':'atnum',
                                'atname':'atname',
                                'atalt':'atalt',
                                'attype':'attype',
                                'resname':'resname',
                                'chain':'chain',
                                'model':'model',
                                'label':'label',
                                'resnum':'resnum',
                                'resext':'resext',
                                'xcoor':'xcoor',
                                'ycoor':'ycoor',
                                'zcoor':'zcoor',
                                'occ':'occ',
                                'b':'b',
                                'segid':'segid',
                                'elem':'elem',
                                'charge':'charge',
                                'group':'group'}

# Initiate chemical information dictionary as pandas DataFrame
cheminfo = DataFrame(STRUCTURE_DATA_INFO)

def set_contact_type(current, add):
  
  current = current.split()
  if 'nd' in current:
    current.remove('nd')
  add = add.split()
  
  return ' '.join(set(current+add))

def remove_contact_type(current, remove):
  
  if not remove in current:
    return current
  
  current = current.split()
  current.remove(remove)
  
  if current:
    return ' '.join(set(current))  
  return 'nd'
  
def coordinates(structure):
  
  """
  TODO: This function should be added to the DataFrame and Series instead
  """
  
  coordinates = structure[['xcoor','ycoor','zcoor']].values
  
  if len(structure) == 1 and len(coordinates) == 1:
    return coordinates[0]
  elif len(coordinates) > 1 and type(coordinates[0]) != type(list):
    return coordinates
    

def eval_water_bridges(contact_frame, structure, min_wbridge_dist=2.5, max_wbridge_dist=4.0, min_omega_angle=75, max_omega_angle=140, min_theta_angle=100, wbfilter=True):
  
  """
  Evaluate the presence of water mediated hydrogen bonded bridges
  in the provided contact DataFrame.
  
  Algorithm:
  1) Select all water oxygen atoms within the range defined by min_wbridge_dist
     (Jiang et al., 2005) - 0.1 and max_wbridge_dist (Jiang et al., 2005) + 0.4.
  2) For each water, get neighbouring atoms below max_wbridge_dist excluding other 
     waters.
  3) In two loops look for ligand donor - water - other acceptor pairs and 
     ligand acceptor - water - other donor pairs.
  4) For each pair check if there is at least one covalently bound hydrogen attached
     to the donor.
  5) Check the theta angle (water O - donor H - donor), should be larger than 
     min_theta_angle (Jiang et al., 2005).
  6) Check the omega angle (acceptor - water O - donor H), should be in the range
     defined by min_omega_angle, max_omega_angle (Jiang et al., 2005).
  7) If wbfilter option is True: a water molecule is only allowed to participate 
     as donor in two hydrogen bonds (two hydrogen atoms as donors). In the case of 
     more than two possible hydrogen bonds for a water molecule as donor, only the 
     two contacts with a water angle closest to 110 deg. and/or smaller 
     H-bond distances are kept.
  """
  
  # Preselect all water oxygens close to ligand
  wbdist = contact_frame[(contact_frame['target','distance'] > min_wbridge_dist) & (contact_frame['target','distance'] <= max_wbridge_dist) 
                          & (contact_frame['target','resname'] == 'HOH') & (contact_frame['target','attype'] == 'O.3')]
  if wbdist.empty:
    return contact_frame
  
  logger.debug("Run water bridge detection on {0} possible contacts using: min_wbridge_dist={1}, max_wbridge_dist={2}, min_omega_angle={3}\
  max_omega_angle={4}, min_theta_angle={5}, wbfilter={6}".format(wbdist.shape[0], min_wbridge_dist, max_wbridge_dist, min_omega_angle,
    max_omega_angle, min_theta_angle, wbfilter))
  
  # Query for potential hbond donor-acceptor pairs
  accpt_attypes = ('N.3','N.2','N.1','N.acid','N.ar','O.3','O.co2','O.2','S.m','S.a','F','Br','Cl')
  donor_attypes = ('N.3','N.2','N.acid','N.am','N.4','N.pl3','N.plc','O.3')
  
  # Loop over waters looking for water bridges
  ligresnum = wbdist['source','resnum'].unique()
  for water in sorted(wbdist['target','resnum'].unique()):
    
    # Get neigbouring atoms
    water = structure.loc[(structure['resnum'] == water) & (structure['attype'] == 'O.3')]
    water_neigh = water.neighbours(cutoff=max_wbridge_dist)
    w = coordinates(water)
    
    # Remove other waters
    if not water_neigh.empty:
      water_neigh = water_neigh[(water_neigh['resname'] != 'HOH')]
    
    # Query possible ligand donor - water - acceptor contacts
    dwa_pairs = []
    for idd,d in water_neigh[(water_neigh['resnum'].isin(ligresnum)) & (water_neigh['attype'].isin(donor_attypes))].iterrows():
      
      donor = structure[structure['atnum'] == d['atnum']]
      covalent_neighbours = donor.neighbours(cutoff=1.6)
      x = coordinates(donor)
    
      # There should at least be covalent neighbours (e.a. not ions etc.)
      if not covalent_neighbours.empty:
      
        # Check if there are H-atoms attached and asses H-bond geometry criteria
        for idy,h in covalent_neighbours[covalent_neighbours['attype'] == 'H'].iterrows():
          y = coordinates(h)
          
          # Check theta angle: donor - hydrogen - water oxygen
          theta = calc_angle(x,y,w)
          if abs(theta) > min_theta_angle:
          
            # Loop over possible acceptors
            for ida,a in water_neigh[~(water_neigh['resnum'].isin(ligresnum)) & (water_neigh['attype'].isin(accpt_attypes))].iterrows():
              acceptor = coordinates(a)
              
              # Check omega angle: acceptor - water oxygen - donor h
              omega = 180-calc_angle(acceptor,w,y)
              if min_omega_angle < abs(omega) < max_omega_angle:
                
                dist_aw = distance(w,acceptor)
                dist_wd = distance(w,x)
                dwa_pairs.append((omega, theta, dist_aw, dist_wd, d['atnum'], a['atnum'], water.atnum.values[0]))
                
                logger.info("Water bridge: donor {0}-{1} {2}-{3}, acceptor {4}-{5} {6}-{7} via {8}-{9}. Dist d-w {10:.2f} a-w {11:.2f}. Omega: {12:.2f} Theta {13:.2f}".format(
                  donor.resnum.values[0], donor.resname.values[0], donor.atnum.values[0], donor.atname.values[0], 
                  a.resnum, a.resname, a.atnum, a.atname, water.resnum.values[0], water.atnum.values[0], dist_wd, dist_aw, omega, theta))
    
    if wbfilter and len(dwa_pairs) > 1:
      dwa_pairs.sort(key=lambda x: (110-x[0])+(x[2]+x[3]))
      dwa_pairs = [dwa_pairs[0]]
    
    for bridge in dwa_pairs:
      cid = contact_frame[(contact_frame['source','atnum'] == bridge[4]) & (contact_frame['target','atnum'] == bridge[6])]
      tid = structure[structure['atnum'] == bridge[5]]
      contact_frame.loc[cid.index, 'contact'] = set_contact_type(contact_frame.loc[cid.index, 'contact'].values[0], 'wb-da')
      contact_frame.loc[cid.index, ('target','angle')] = bridge[1]
      
      newindex = contact_frame.index.max()+1
      contact_frame.loc[newindex,'contact'] = 'wb-da'
      contact_frame.loc[newindex,('target','distance')] = bridge[2]
      contact_frame.loc[newindex,('target','angle')] = bridge[0]
      
      for mdx in ('segid','chain','resname','resnum','atname','atnum','attype','elem'):
        contact_frame.loc[newindex,('target',mdx)] = cid['target',mdx].values[0]
        contact_frame.loc[newindex,('source',mdx)] = tid[mdx].values[0]
      
    # Query possible ligand acceptor - water - donor contacts
    awd_pairs = []
    for ida,a in water_neigh[(water_neigh['resnum'].isin(ligresnum)) & (water_neigh['attype'].isin(accpt_attypes))].iterrows():
      acceptor = coordinates(a)
      
      # Loop over possible donors
      for idd,d in water_neigh[~(water_neigh['resnum'].isin(ligresnum)) & (water_neigh['attype'].isin(donor_attypes))].iterrows():
        
        donor = structure[structure['atnum'] == d['atnum']]
        covalent_neighbours = donor.neighbours(cutoff=1.6)
        x = coordinates(donor)
        
        # There should at least be covalent neighbours (e.a. not ions etc.)
        if not covalent_neighbours.empty:
      
          # Check if there are H-atoms attached and asses H-bond geometry criteria
          for idy,h in covalent_neighbours[covalent_neighbours['attype'] == 'H'].iterrows():
            y = coordinates(h)
                        
            # Check theta angle: donor - hydrogen - water oxygen
            theta = calc_angle(x,y,w)
            if abs(theta) > min_theta_angle:
              
              # Check omega angle: acceptor - water oxygen - donor h
              omega = 180 - calc_angle(acceptor,w,y)
              if min_omega_angle < abs(omega) < max_omega_angle:
                
                dist_aw = distance(w,acceptor)
                dist_wd = distance(w,x)
                awd_pairs.append((omega, theta, dist_aw, dist_wd, d['atnum'], a['atnum'], water.atnum.values[0]))
                
                logger.info("Water bridge: donor {0}-{1} {2}-{3}, acceptor {4}-{5} {6}-{7} via {8}-{9}. Dist d-w {10:.2f} a-w {11:.2f}. Omega: {12:.2f} Theta {13:.2f}".format(
                  donor.resnum.values[0], donor.resname.values[0], donor.atnum.values[0], donor.atname.values[0], 
                  a.resnum, a.resname, a.atnum, a.atname, water.resnum.values[0], water.atnum.values[0], dist_wd, dist_aw, omega, theta))
    
    if wbfilter and len(awd_pairs) > 2:
      awd_pairs.sort(key=lambda x: (110-x[0])+(x[2]+x[3]))
      awd_pairs = awd_pairs[:2]
      
    for bridge in awd_pairs:
      cid = contact_frame[(contact_frame['source','atnum'] == bridge[5]) & (contact_frame['target','atnum'] == bridge[6])]
      tid = structure[structure['atnum'] == bridge[4]]
      contact_frame.loc[cid.index, 'contact'] =  set_contact_type(contact_frame.loc[cid.index, 'contact'].values[0], 'wb-ad')
      contact_frame.loc[cid.index, ('target','angle')] = bridge[1]
      
      newindex = contact_frame.index.max()+1
      contact_frame.loc[newindex,'contact'] = 'wb-ad'
      contact_frame.loc[newindex,('target','distance')] = bridge[2]
      contact_frame.loc[newindex,('target','angle')] = bridge[0]
      
      for mdx in ('segid','chain','resname','resnum','atname','atnum','attype','elem'):
        contact_frame.loc[newindex,('target',mdx)] = cid['target',mdx].values[0]
        contact_frame.loc[newindex,('source',mdx)] = tid[mdx].values[0]
    
  return contact_frame

def eval_hbonds(contact_frame, structure, max_hbond_dist=4.1, hbond_don_anglediv=50, hbond_acc_anglediv=90, optimize=True):
  
  """
  Evaluate the presence of hydrogen bonded contacts in the provided 
  contact DataFrame. This function does not evaluate water bridges.
  
  Prerequisits:
  This function uses the SYBYL atom types to identify possible 
  hydrogen bond donor and acceptor atoms. At least one covalently 
  bonded hydrogen is expected for donors and subsequently the 
  possible bonding geometry in terms of distances and angles is 
  evaluated. 
  
  As a result the function requires the input structure to be fully
  protonated or having at least polar hydrogens attached. 
  The geometry of the attached hydrogens influences the contacts 
  identified. If the structure is not, or partially protonated, the 
  method used to add hydrogens will influence the identified contacts.
  Structure derived from moleculare dynamics will likely having their
  (polar) hydrogens oriented as such to reflect a hydrogen bond if
  present. If hydrogens are added with another program this may not 
  be the case. OpenBabel for instance will add hydrogens in standard
  conformation not taking into account the environment of the atom 
  to wich hydrogens are attached. The HBplus program (McDonald I K & 
  Thornton J M (1994). J. Mol. Biol., 238, 777-793.) also part of 
  the LIGPLOT program, will optimize local hydrogen geometry first.
  
  Differences in the geometry of added hydrogens will mostly affect
  the angle critera rather than the distance. To correct for
  non-optimized H-atom geometry without the need for optimization, 
  the function allows the angle critera to be a function of the 
  number of attached atoms using the 'optimize' option. Angles are
  then defined as:
  
    180 / number of non-isolated covalent neigbours - 1
  
  for all donors that are not trigonal planar (N.pl3, N.plc, N.ar, 
  N.2, O.2, O.co2, S.a)
  
  Algorithm:
  1) Select all heavy atom contacts within max_hbond_dist not involving
     waters.
  2) Identify donor-acceptor pairs for source to target and target to 
     source based on SYBYL atom types (see below).
  3) Check if donor has at least one covalently bonded H-atom
  4) Check is angle between donor - H - acceptor does not deviate more
     than hbond_don_anglediv from it's ideal in-plane (180) degree
     orientation (cone fit), (Hubbard & Haider, 2001). The value for
     hbond_don_anglediv is either fixed or a function of the number
     of covalently attached atoms (see above) when 'optimize' is True.
  5) Check is the angle between the heavy atom acceptor neighbour -
     acceptor - H does not deviate more than hbond_acc_anglediv.
    
  atom descriptor       base type   donor1  acceptor    directionality
  --------------------------------------------------------------------
  sp3 N                  N.3        y       y           along lone pair
  sp2 N                  N.2        y       y           along lone pair
  sp  N                  N.1        n       y           along lone pair
  Acidic N               N.acid     y       y           along lone pair 2
  Aromatic N             N.ar       y       y           along lone pair
  Amide N                N.am       y       n
  Quaternary N           N.4        y       n
  Uncharged trigonal N   N.pl3      y       n           3
  Charged trigonal N     N.plc      y       n           4
  Hydroxyl O             O.3        y       y           in plane of lone pair
  Ether O                O.3        n       y           in plane of lone pair
  Carboxylate O          O.co2      n       y           along lone pair  
  Carbonyl O             O.2        n       y           in plane of lone pair
  Nitro O                O.2        n       y           along lone pair 
  N-oxide O              O.2        n       y
  Amide O                O.2        n       y           in plane of lone pair
  Neutral sulfur-bound O O.2        n       y           5
  Charged sulfur-bound O O.co2      n       y           cone 6
  Phosphate O            O.co2      n       y           cone
  Borate O               O.co2      n       y           cone
  Other neg-charged O    O.co2      n       y
  Negative charged S     S.m        n       y           along lone pair 
  sp2 S                  S.a        n       y           along lone pair 
  
  1: Provided at least one H-atom covalently bound
  2: An acidic nitrogen is a nitrogen bound by at least two single bonds
  3: As in uncharged histidine residue
  4: As in a guanidino residue
  5: As in sulfonamides, sulfoxides, sulfones
  6: As in sulphate groups
  
  :param contact_frame: LIEContactFrame
  :param structure: Pandas DataFrame representing the structure
  :param max_hbond_dist: Maximum hydrogen bond distance cutoff
  :param hbond_don_anglediv: Maximum hydrogen bond donor-H-acceptor
                             angle deviation.
  :param hbond_acc_anglediv: Maximum hydrogen bond acceptor'-acceptor-H
                             angle deviation.
  :param optimize: Rather to optimize angle cutoff based on donor atom
                   geometry.
  
  :return: Changes the 'contact' label in the contact_frame to hb-ad (hydrogen
           bond acceptor-donor) or hb-da (hydrogen bond donor-acceptor) for
           identified hydrogen-bonded contacts. Also add the value of the 
           donor-H-acceptor angle.
  """
  
  # Preselect all contacts below max_hbond_dist not involving waters
  hbdist = contact_frame[(contact_frame['target','distance'] <= max_hbond_dist) & (contact_frame['target','resname'] != 'HOH')]
  if hbdist.empty:
    return contact_frame
  
  logger.debug("Run hydrogen bond detection on {0} possible contacts using: max_hbond_dist={1}, hbond_don_anglediv={2}, optimize={3}".format(
    hbdist.shape[0], max_hbond_dist, hbond_don_anglediv, optimize))
  anglediv = copy.copy(hbond_don_anglediv)
  
  # Query for potential hbond donor-acceptor pairs
  accpt_attypes = ('N.3','N.2','N.1','N.acid','N.ar','O.3','O.co2','O.2','S.m','S.a')
  donor_attypes = ('N.3','N.2','N.acid','N.am','N.ar','N.4','N.pl3','N.plc','O.3')
  
  # First define 'source' as donor and 'target' as acceptor
  donor_acceptor = hbdist[(hbdist['source','attype'].isin(donor_attypes)) & (hbdist['target','attype'].isin(accpt_attypes))]
  logger.debug("{0} contacts after selecting for donor-acceptor pairs".format(donor_acceptor.shape[0]))
  
  # Ensure donors have at least one H-atom covalently bound
  for idx,n in donor_acceptor.iterrows():
    donor = structure[structure['atnum'] == n['source','atnum']]
    covalent_neighbours = donor.neighbours(cutoff=1.6)
    
    # There should at least be covalent neighbours (e.a. not ions etc.)
    if not covalent_neighbours.empty:
      
      # Check if there are H-atoms attached and asses H-bond geometry criterea
      for idy,h in covalent_neighbours[covalent_neighbours['attype'] == 'H'].iterrows():
        x = coordinates(donor)
        y = coordinates(h)
        
        acceptor = structure.loc[structure['atnum'] == n['target','atnum']]
        acceptor_neigh = acceptor.neighbours(cutoff=1.6)
        if not acceptor_neigh.empty:
          acceptor_neigh = acceptor_neigh[acceptor_neigh['attype'] != 'H'].head(1)
        z = coordinates(acceptor)
        
        # Angle donor - H - acceptor
        angle1 = calc_angle(x,y,z)
        
        # Angle acceptor_neigh - acceptor - H
        angle2 = 100
        if not acceptor_neigh.empty:
          zz = coordinates(acceptor_neigh)
          angle2 = calc_angle(zz,z,y)
        
        # If optimize equals True, determine donor-H-acceptor angle deviation based on covalent bonding 
        # geometry for all non trigonal planar donor atoms
        hbond_don_anglediv = anglediv
        if optimize and not donor['attype'].values[0] in ('N.pl3', 'N.plc', 'N.ar', 'N.2', 'O.2', 'O.co2', 'S.a'):
          substitutions = 0
          for idz,i in covalent_neighbours.iterrows():
            r = structure.loc[structure['atnum'] == i['atnum']].neighbours(cutoff=1.6)
            if len(r) > 1: substitutions += 1
          hbond_don_anglediv = (180 / float(substitutions))
        
        if (180-hbond_don_anglediv < abs(angle1) < 180+hbond_don_anglediv) and (180-hbond_acc_anglediv < abs(angle2) < 180+hbond_acc_anglediv):
          contact_frame.loc[idx, 'contact'] = set_contact_type(contact_frame.loc[idx, 'contact'].values[0], 'hb-da')
          contact_frame.loc[idx, ('target','angle')] = angle1
          logger.info("H-bond between {0}-{1} {2}-{3} and {4}-{5} {6}-{7}. Distance D-A: {8:.3f}A, angle: {9:.2f} deg. hbond_don_anglediv: {10:.2f}".format(
            contact_frame.loc[idx, 'source'].resnum, contact_frame.loc[idx, 'source'].resname, contact_frame.loc[idx, 'source'].atnum,
            contact_frame.loc[idx, 'source'].atname, contact_frame.loc[idx, 'target'].resnum, contact_frame.loc[idx, 'target'].resname,
            contact_frame.loc[idx, 'target'].atnum, contact_frame.loc[idx, 'target'].atname, contact_frame.loc[idx, 'target'].distance, angle1, hbond_don_anglediv
          ))
              
  # Next define 'target' as donor and 'source' as acceptor  
  acceptor_donor = hbdist[(hbdist['source','attype'].isin(accpt_attypes)) & (hbdist['target','attype'].isin(donor_attypes))]
  logger.debug("{0} contacts after selecting for acceptor-donor pairs".format(acceptor_donor.shape[0]))
  
  # Ensure donors have at least one H-atom covalently bound
  for idx,n in acceptor_donor.iterrows():
    donor = structure[structure['atnum'] == n['target','atnum']]
    covalent_neighbours = donor.neighbours(cutoff=1.6)
    
    if not covalent_neighbours.empty:
      for idy,h in covalent_neighbours[covalent_neighbours['attype'] == 'H'].iterrows():
        x = coordinates(donor)
        y = coordinates(h)
        
        acceptor = structure.loc[structure['atnum'] == n['source','atnum']]
        acceptor_neigh = acceptor.neighbours(cutoff=1.6)
        if not acceptor_neigh.empty:
          acceptor_neigh = acceptor_neigh[acceptor_neigh['attype'] != 'H'].head(1)
        z = coordinates(acceptor)
        
        # Angle donor - H - acceptor
        angle1 = calc_angle(x,y,z)
        
        # Angle acceptor_neigh - acceptor - H
        angle2 = 100
        if not acceptor_neigh.empty:
          zz = coordinates(acceptor_neigh)
          angle2 = calc_angle(zz,z,y)
        
        # If optimize equals True, determine donor-H-acceptor angle deviation based on covalent bonding 
        # geometry for all non trigonal planar donor atoms
        hbond_don_anglediv = anglediv
        if optimize and not donor['attype'].values[0] in ('N.pl3', 'N.plc', 'N.ar', 'N.2', 'O.2', 'O.co2', 'S.a'):
          substitutions = 0
          for idz,i in covalent_neighbours.iterrows():
            r = structure.loc[structure['atnum'] == i['atnum']].neighbours(cutoff=1.6)
            if len(r) > 1: substitutions += 1
          hbond_don_anglediv = (180 / float(substitutions))
        
        if (180-hbond_don_anglediv < abs(angle1) < 180+hbond_don_anglediv) and (180-hbond_acc_anglediv < abs(angle2) < 180+hbond_acc_anglediv):
          contact_frame.loc[idx, 'contact'] = set_contact_type(contact_frame.loc[idx, 'contact'].values[0], 'hb-ad')
          contact_frame.loc[idx, ('target','angle')] = angle1
          logger.info("H-bond between {0}-{1} {2}-{3} and {4}-{5} {6}-{7}. Distance D-A: {8:.3f}A, angle: {9:.2f} deg. hbond_don_anglediv: {10:.2f}".format(
            contact_frame.loc[idx, 'source'].resnum, contact_frame.loc[idx, 'source'].resname, contact_frame.loc[idx, 'source'].atnum,
            contact_frame.loc[idx, 'source'].atname, contact_frame.loc[idx, 'target'].resnum, contact_frame.loc[idx, 'target'].resname,
            contact_frame.loc[idx, 'target'].atnum, contact_frame.loc[idx, 'target'].atname, contact_frame.loc[idx, 'target'].distance, angle1, hbond_don_anglediv
          ))
  
  return contact_frame

def eval_halogen_bonds(contact_frame, structure, max_halogen_dist=4.1, halogen_don_angle=165, halogen_acc_angle=120, halogen_angle_dev=30, halogens=('I','Br','Cl','F')):
  
  """
  Reference: P. Auffinger, Halogen bonds in biological molecules (2004), PNAS: vol. 101 no. 38. vol. 16789-16794
  """
  
  # Preselect all contacts between source halogen and target oxygen,nitrogen or sulfur below max_halogen_dist not involving waters
  hadist = contact_frame[(contact_frame['source','attype'].isin(halogens)) & 
                         (contact_frame['target','distance'] <= max_halogen_dist) & 
                         (contact_frame['target','elem'].isin(('O','N','S'))) & 
                         (contact_frame['target','resname'] != 'HOH')]
  
  if hadist.empty:
    return contact_frame
  
  logger.debug("Run halogen bond detection on {0} possible contacts using: max_halogen_dist={1}, halogen_don_angle={2}, halogen_acc_angle={3}, halogen_angle_dev={4}".format(
    hadist.shape[0], max_halogen_dist, halogen_don_angle, halogen_acc_angle, halogen_angle_dev))
  
  for idx,n in hadist.iterrows():
    
    source = structure[structure['atnum'] == n['source','atnum']]
    source_neighbours = source.neighbours(cutoff=1.6)
    target = structure[structure['atnum'] == n['target','atnum']]
    target_neighbours = target.neighbours(cutoff=1.6)
    
    # Ensure source (halogen) only has carbon as single neighbour
    c = source_neighbours[source_neighbours['elem'] == 'C']
    c_neigh = list(source_neighbours.loc[source_neighbours['attype'] != 'H', 'elem'].values)
    if c_neigh.count('C') != 1 or len(c_neigh) > 1:
      continue
    
    # Ensure the target (oxygen, nitrogen, sulfur) only has C,P,S as single neighbour
    y = target_neighbours[target_neighbours['elem'].isin(('P','C','S'))]
    y_neigh = list(target_neighbours.loc[target_neighbours['elem'].isin(('P','C','S')), 'elem'].values)
    if sum([y_neigh.count(n) for n in ('C','P','S')]) == 0 or not len(y_neigh):
      continue
    
    # Calculate donor (C-X -- O) and acceptor (Y-O -- X) angles 
    donor_angle = calc_angle(coordinates(c), coordinates(source), coordinates(target))
    acceptor_angle = calc_angle(coordinates(y), coordinates(target), coordinates(source))
    if (halogen_don_angle-halogen_angle_dev < abs(donor_angle) < halogen_don_angle+halogen_angle_dev) and (halogen_acc_angle-halogen_angle_dev < abs(acceptor_angle) < halogen_acc_angle+halogen_angle_dev):
      contact_frame.loc[idx, 'contact'] = set_contact_type(contact_frame.loc[idx, 'contact'].values[0], 'xb')
      contact_frame.loc[idx, ('target','angle')] = donor_angle
      logger.info("Halogen bond between {0}-{1} {2}-{3} and {4}-{5} {6}-{7}. Distance D-A: {8:.3f}A, donor angle: {9:.2f} deg. acceptor angle: {10:.2f}".format(
        source.resnum.values[0], source.resname.values[0], source.atnum.values[0], source.atname.values[0], 
        target.resnum.values[0], target.resname.values[0], target.atnum.values[0], target.atname.values[0], 
        contact_frame.loc[idx, 'target'].distance, donor_angle, acceptor_angle))
    
  return contact_frame

def eval_saltbridge(contact_frame, structure, max_charge_dist=5.5, use_partial_charge=False, neg_cutoff=-0.3, pos_cutoff=0.3):
  
  """
  Evaluate contacts between centers of positive and negative charge.
  Physiological relevant pH is assumed.
  
  max_charge_dist according to (Barlow and Thornton, 1983) + 1.5A
  
  Positive or negative charge is assigned to amino-acid and ligand 
  SYBYL atom types according to the table below. 
  In addition, information from the charge column is read if available
  in the structure object.
  
  Contacts between all charge pairs will be marked with sb-np and sb-pn
  for negative-positive and positive-negative ligand-protein contacts.
   
  amino-acid                  type   atom         charge
  --------------------------------------------------------------------
  Arginine - Arg - R          N.pl3  RNHC(NH2)2+  +
  Lysine - Lys - K            N.4    RNH3         +
  Histidine - His - H         N.ar   ND1, NE2     +
  Aspartic acid - Asp - D     O.co2  RCOO-        -
  Glutamic acid - Glu - E     O.co2  RCOO-        -
    
  Ligands                     type   atom         charge
  --------------------------------------------------------------------
  quaterny ammonium           N.4                 +
  tertiary amines             N.am                +
  sulfonium groups            S.3                 +
  guanidine groups            C.cat               +
  phosphate                   O.co2  PO4          -
  sulfonate                   S.3    RSO2O-       -
  sulfonic acid               S.O2                -
  carboxylate                 O.co2               -
  
  :param contact_frame: LIEContactFrame
  :param structure: Pandas DataFrame representing the structure
  :param max_charge_dist: Maximum distance cutoff between charge centers
  
  :return: Changes the 'contact' label in the contact_frame to sb-pn
           (salt-bridge between negative ligand center and positive others)
           or sb-pn (salt-bridge between positive ligand center and
           negative others).
  """
  
  # Preselect all contacts below max_charge_dist
  chdist = contact_frame[contact_frame['target','distance'] <= max_charge_dist]
  if chdist.empty:
    return contact_frame
  
  logger.debug("Run salt-bridge detection on {0} possible contacts using: max_charge_dist={1}, use_partial_charge={2}, neg_cutoff={3}, pos_cutoff={4}".format(
    chdist.shape[0], max_charge_dist, use_partial_charge, neg_cutoff, pos_cutoff))
    
  # Check if we have charge column in structure and get charged atoms from there if use_partial_charge
  neg_charge, pos_charge = [], []
  if use_partial_charge:
    if 'charge' in structure.columns:
      neg_charge = structure.loc[structure['charge'] < neg_cutoff, 'atnum'].values
      pos_charge = structure.loc[structure['charge'] > pos_cutoff, 'atnum'].values
      if neg_charge.size or pos_charge.size:
        logger.debug("Found {0} postive, and {1} negative charged atoms using structure charge column".format(
          pos_charge.size, neg_charge.size)) 
  
  # Query Positive amino-acid to negative ligand types. Use default definitions and charged atoms found in
  # structure charge column if any
  aa  = ('ARG','LYS','HIS')
  pos = ('N.4','N.pl3','N.ar')
  neg = ('O.co2','O.3','S.O2','S.3')
  pos_neg = chdist[(chdist['source','attype'].isin(neg) | chdist['source','atnum'].isin(neg_charge)) &
                   ((chdist['target','attype'].isin(pos) & chdist['target','resname'].isin(aa)) | chdist['source','atnum'].isin(pos_charge))]
  
  logger.info("{0} contacts after selecting for postive amino-acid to negative ligand atoms".format(pos_neg.shape[0]))
  
  if not pos_neg.empty: 
    contact_frame.loc[pos_neg.index, 'contact'] = set_contact_type(contact_frame.loc[pos_neg.index, 'contact'].values[0], 'sb-np')

  # Query Negative amino-acid to positive ligand types. Use default definitions and charged atoms found in
  # structure charge column if any
  aa  = ('ASP','GLU')
  pos = ('N.4','N.am','C.cat','S.3')
  neg = ['O.co2']
  neg_pos = chdist[(chdist['source','attype'].isin(pos) | chdist['source','atnum'].isin(pos_charge)) &
                   ((chdist['target','attype'].isin(neg) & chdist['target','resname'].isin(aa)) | chdist['source','atnum'].isin(neg_charge))]

  logger.info("{0} contacts after selecting for negative amino-acid to positive ligand atoms".format(neg_pos.shape[0]))
  
  if not neg_pos.empty:
    contact_frame.loc[neg_pos.index, 'contact'] = set_contact_type(contact_frame.loc[neg_pos.index, 'contact'].values[0], 'sb-pn')
      
  return contact_frame
  
def eval_hydrophobic_interactions(contact_frame, structure, hydroph_dist_max=4.0):
  
  """
  Evaluate hydrophobic-lipophilic contacts.
  Contact is marked hydrophobic if both atoms involved in the contact are carbons,
  have only carbon or hydrogen atoms as neighbours and their distance is lower than 
  hydroph_dist_max.
  
  The number of hydrophobic contacts is reduced in size by appyling two filter steps:
  - If the the atom pair is already involved in hydrophobic interactions between 
    rings interacting via phi-stacking they are not assigned as stacking is a form of
    hydrophobic interactions. This does require the stacking routine to be run first.
  - If one ligand atom contacts multiple target atoms, the one with the smallest 
    distance is kept.
  """
  
  hfob_atom_list = set(['C.3','C.2','C.1','C.ar','H'])
  hfobdist = contact_frame[(contact_frame['source','attype'].isin(('C.3','C.2','C.1','C.ar'))) & 
                           (contact_frame['target','attype'].isin(('C.3','C.2','C.1','C.ar'))) &
                           (contact_frame['target','distance'] < hydroph_dist_max)]
  
  if hfobdist.empty:
    return contact_frame
  
  logger.debug("Run hydrophobic interaction detection on {0} possible contacts using: hydroph_dist_max={1}".format(hfobdist.shape[0], hydroph_dist_max))
  
  for idx,n in hfobdist.iterrows():
    source = structure[structure['atnum'] == n['source','atnum']]
    target = structure[structure['atnum'] == n['target','atnum']]
    source_neighbours = source.neighbours(cutoff=1.6)
    target_neighbours = target.neighbours(cutoff=1.6)
    if len(set(source_neighbours['attype']).difference(hfob_atom_list)) == 0 and len(set(target_neighbours['attype']).difference(hfob_atom_list)) == 0:
      contact_frame.loc[idx, 'contact'] = set_contact_type(contact_frame.loc[idx, 'contact'].values[0], 'hf')
  
  # Cluster based on atom-atom contacts
  hf = contact_frame[contact_frame['contact'] == 'hf']
  if not hf.empty:
    for atom in hf['target','atnum'].unique():
      selection = hf[hf['target','atnum'] == atom]
      
      if selection.shape[0] > 1:
        logger.debug("{0} hydrophobic contacts identified to atom {1:.0f}. Keeping one with smallest distance".format(selection.shape[0],atom))
        reset = selection[selection['target','distance'] != selection['target','distance'].min()].index
        contact_frame.loc[reset.values,'contact'] = remove_contact_type(contact_frame.loc[reset.values, 'contact'].values[0],'hf')
        
  return contact_frame

def eval_heme_coordination(contact_frame, structure, rings=[], heme_dist_prefilter=5.5, heme_dist_max=3.5, heme_dist_min=0, min_heme_coor_angle=105, max_heme_coor_angle=160, 
                           fe_ox_dist=1.6, exclude=('H','O.3','O.2','O.co2','O.spc','O.t3p','C.cat','S.o2')):
  
  """
  Evaluate heme coordination of ligand atoms
  """
  
  # Select all atoms within heme_dist_prefilter distance from Fe excluding atoms in exclude list
  fedist = contact_frame[(contact_frame['target','atname'] == 'FE') & 
                         (~contact_frame['source','attype'].isin(exclude)) &
                         (contact_frame['target','distance'] < heme_dist_prefilter)]
  if fedist.empty:
    return contact_frame
  
  # Get Fe atom
  fe = structure[(structure['resname'] == 'HEM') & (structure['atname'] == 'FE')]
  if fe.empty:
    logger.warn("Unable to asses heme coordination. Fe atom not found")
    return contact_frame
    
  # Get four nitrogen atoms coordinating the Fe atom
  fe_neigh = fe.neighbours(cutoff=3)
  fe_coordinating = fe_neigh[(fe_neigh['resname'] == 'HEM') & (fe_neigh['elem'] == 'N')].sort_values(by='atname')
  if len(fe_coordinating) != 4:
    logger.warn("Unable to asses heme coordination. Found {0} Heme nitrogen atoms coordinating Fe. Expected 4".format(len(fe_coordinating)))
    return contact_frame
  
  logger.debug("Run heme coordination detection on {0} possible contacts using: heme_dist_prefilter={1:.2f}, heme_dist_min={2:.2f}, heme_dist_max={3:.2f}\
  min_heme_coor_angle={4:.2f}, max_heme_coor_angle={5:.2f}, fe_ox_dist={6:.2f}".format(fedist.shape[0], heme_dist_prefilter, heme_dist_min, heme_dist_max,
  min_heme_coor_angle, max_heme_coor_angle, fe_ox_dist))
  
  # Calculate normals between Nitrogens -> Fe vectors
  fe_coor = fe[['xcoor','ycoor','zcoor']].values[0]
  n_coor = fe_coordinating[['xcoor','ycoor','zcoor']].values - fe_coor
  
  m1 = numpy.cross(n_coor[0], n_coor[1])
  m2 = numpy.cross(n_coor[1], n_coor[2])
  m3 = numpy.cross(n_coor[2], n_coor[3])
  m4 = numpy.cross(n_coor[3], n_coor[0])
  
  # Calculate dummy O atom from the average of the four normals
  # Normalize normal mean, change vector size to 1.6 A and set point
  mv = numpy.mean(numpy.vstack((m1,m2,m3,m4)), axis=0)
  dummyox = ((mv/numpy.linalg.norm(mv)) * fe_ox_dist)+fe_coor
  logger.info("Reconstructed oxygen atom placed {0}A above Heme Fe at position {1}".format(fe_ox_dist, ' '.join(['{0:.3f}'.format(c) for c in dummyox])))
  
  # Check the coordination of the Fe atom by the SG atom of the Cys below Heme
  sg = fe_neigh[(fe_neigh['resname'] == 'CYS') & (fe_neigh['atname'] == 'SG')]
  if not sg.empty:
    sg_angle = calc_angle(dummyox, fe_coor, sg[['xcoor','ycoor','zcoor']].values[0])
    if not 160 < sg_angle < 200:
      logger.warn("Angle between reconstructed oxygen -> Fe -> Cys SG has unusual value {0:.3f}".format(sg_angle))
  else:
    logger.warn("No CYS SG atom in a distance of 3.0A of the Heme Fe atom")
  
  # Check if there are rings with there center of mass below heme_dist_prefilter from heme FE.
  # Calculate ring normals
  ring_normals = []
  for ring in rings:  
    aromatic = structure.loc[ring,:]
    aromatic_center = center_of_mass(aromatic)
    aromatic_fe_dist = distance(fe_coor, aromatic_center)
    if aromatic_fe_dist < heme_dist_prefilter:
      aromatic_center, aromatic_norm = plane_fit(aromatic[['xcoor','ycoor','zcoor']].values, center=aromatic_center)
      aromatic_norm_angle = angle(aromatic_norm, mv, deg=True)
      aromatic_norm_angle = min(aromatic_norm_angle, 180-aromatic_norm_angle if not 180-aromatic_norm_angle < 0 else aromatic_norm_angle)
      ring_normals.append((aromatic_center, aromatic_norm, aromatic_norm_angle, ring))
      
      logger.info("Ring {0} close to heme Fe: distance center-Fe {1:.2f} A, normal angle heme plane-ring: {2:.2f} deg.".format(ring, aromatic_fe_dist, aromatic_norm_angle))
  
  # Get ligand atoms coordinated
  for idx,n in fedist.iterrows():
    
    source = structure[structure['atnum'] == n['source','atnum']]
    source_atom_type = n['source','attype']
    z = coordinates(source)
    
    # Check for heme coordination by aromatic nitrogens. label as 'hc'
    if source_atom_type in ('N.ar','N.2','N.3'):
      ar_norm_angle = 90
      for ring in ring_normals:
        if n['source','atnum'] in ring[-1]:
          ar_norm_angle = ring[2]
          break
      fe_dist = distance(z, fe_coor)
      fe_offset = distance(projection(mv, fe_coor, z), fe_coor)
      if 45 < ar_norm_angle < 95 and fe_dist < 3.5 and fe_offset < 1.0:
        contact_frame.loc[idx, 'contact'] = set_contact_type(contact_frame.loc[idx, 'contact'].values[0], 'hc')
        contact_frame.loc[idx, ('target','angle')] = ar_norm_angle
        logger.info("Heme Fe coordination with {0} {1}. Distance: {2:.2f} A. offset: {3:.2f} A plane normal angle: {4:.2f}".format(n['source','atnum'], 
          n['source','atname'], fe_dist, fe_offset, ar_norm_angle))
    
    # Check for possible sites of metabolism and label as 'hm'.
    # Filter on covalent neighbours and apply knowledge based rules.
    if source_atom_type in ('C.2','C.3','C.ar','N.1','N.2','N.4','N.pl3','S.3'):
      cutoff=1.6
      if source_atom_type == 'S.3': cutoff = 1.8
      neigh = source.neighbours(cutoff=cutoff)
      neigh_atom_types = set(neigh['attype'])
      
      # If ligand atom is of type C.3 or C.ar it should contain at least one covalently bonded atom of type ['H','Cl','I','Br','F','Hal']
      if source_atom_type in ('C.3','C.ar') and len(neigh_atom_types.intersection(set(['H','Cl','I','Br','F','Hal']))) == 0:
        logger.debug("Ligand target atom {0}-{1} excluded. Atom type {2} not covalently bonded to: H,Cl,I,Br,F or Hal".format(
          n['source','atnum'], n['source','atname'], source_atom_type))
        continue
      
      # If ligand atom is of type N.4 it should contain at least one covalently bonded atom of type H
      if source_atom_type == 'N.4' and not 'H' in neigh_atom_types:
        logger.debug("Ligand target atom {0}-{1} excluded. Atom type N.4 not covalently bonded to hydrogen".format(
          n['source','atnum'], n['source','atname']))
        continue
      
      # Exclude carbons that are a part of ketone or carboxylate
      if source_atom_type == 'C.2' and 'O.2' in neigh_atom_types or 'O.co2' in neigh_atom_types:
        logger.debug("Ligand target atom {0}-{1} excluded. Atom type C.2 part of ketone or carboxylate group.".format(
          n['source','atnum'], n['source','atname']))
        continue
      
      # Additional check on S.O2 wrongly labeled as S.3 (PLANTS?)
      if source_atom_type == 'S.3' and neigh[neigh['attype'] == 'O.2'].shape[0] == 2:
        logger.debug("Ligand target atom {0}-{1} excluded. Atom labeled as S.3 but probably S.O2 as it is covalently bonded to two O.2".format(
          n['source','atnum'], n['source','atname']))
        continue
      
      # If N.pl3 or N.2 check for nitro- or nitrate group.
      if source_atom_type in ('N.pl3','N.2') and ('O.co2' in neigh_atom_types or len(neigh_atom_types.intersection(set(['O.2','O.3']))) == 2):
        logger.debug("Ligand target atom {0}-{1} excluded. Atom type {2}, exclude nitro- nitrate group".format(
          n['source','atnum'], n['source','atname'], source_atom_type))
        continue
      
      # Exclude (iso)-nitrile group
      if source_atom_type in 'N.1' and 'C.1' in neigh_atom_types:
        logger.debug("Ligand target atom {0}-{1} excluded. Carbon with Sp hybridized N".format(n['source','atnum'], n['source','atname']))
        continue
      
      # Check Heme-Nitrogen coordination (Type II binding). 
      if source_atom_type in ('C.ar','N.ar'):
        ar_norm_angle = None
        for ring in ring_normals:
          if n['source','atnum'] in ring[-1]:
            ar_norm_angle = ring[2]
            break
        if ar_norm_angle and not (45 < ar_norm_angle < 85 or 95 < ar_norm_angle < 135):
          logger.debug("Ligand target atom {0}-{1} excluded. Aromatic C or N part of ring with angle of {2:.2f} with respect to Heme plane".format(
            n['source','atnum'], n['source','atname'], ar_norm_angle))
          continue
    
    fe_ox_angle = calc_angle(fe_coor, dummyox, z[0])
    dist = distance(dummyox, z)
    if min_heme_coor_angle < abs(fe_ox_angle) < max_heme_coor_angle and heme_dist_min < dist < heme_dist_max:          
      contact_frame.loc[idx, 'contact'] = set_contact_type(contact_frame.loc[idx, 'contact'].values[0], 'hm')
      contact_frame.loc[idx, ('target','angle')] = fe_ox_angle
      logger.info("Heme Fe possible som with {0} {1}. Distance: {2:.3f} A. FE-O-X angle: {3:.3f}".format(n['source','atnum'], n['source','atname'], dist, fe_ox_angle))
    else:
      logger.debug("Ligand target atom {0}-{1} excluded. Angle ({2:.3f}) or distance ({3:.3f}) criteria violated".format(
        n['source','atnum'], n['source','atname'], fe_ox_angle, dist))
        
  return contact_frame

def eval_pication(contact_frame, structure, pication_dist_max=6.0, pication_offset_max=2.0, pication_amine_angle_min=90, use_partial_charge=False, pos_cutoff=0.3):
  
  """
  Evaluate pi-Cation interaction between aromatic rings and positively charged groups.
  """
  
  # Check if we have charge column in structure and get charged atoms from there if use_partial_charge
  pos_charge = []
  if use_partial_charge:
    if 'charge' in structure.columns:
      pos_charge = structure.loc[structure['charge'] > pos_cutoff, 'atnum'].values
      if pos_charge.size:
        logger.debug("Found {0} postive charged atoms using structure charge column".format(pos_charge.size))
  
  # Select all atoms where a positive charged ligand atom is close to a aromatic amino-acid
  pcdist = contact_frame[((contact_frame['source','attype'].isin(('N.3','N.4','N.am','C.cat','S.3'))) | (contact_frame['source','attype'].isin(pos_charge))) &
                         (contact_frame['target','resname'].isin(('PHE','HIS','TRP','TYR')) &
                         (contact_frame['target','distance'] < pication_dist_max+1))]
  
  if pcdist.empty:
    return contact_frame
  
  logger.debug("Run pi-cation detection on {0} possible contacts using: pication_dist_max={1}, pication_offset_max={2}, pication_amine_angle_min={3},\
 use_partial_charge={4}, pos_cutoff={5}".format(pcdist.shape[0], pication_dist_max, pication_offset_max, pication_amine_angle_min, use_partial_charge, pos_cutoff))
  
  aaringcenters = {}
  for ring in pcdist['target','resnum'].unique():
    aa = structure[structure['resnum'] == ring]
    resname = aa['resname'].unique()[0]
    if resname == 'PHE':
      coor = aa[(aa['resname'] == 'PHE') & ((aa['atname'].isin(('CG','CD1','CD2','CE1','CE2','CZ'))) | (aa['attype'] == 'C.ar'))]
    elif resname == 'HIS':
      coor = aa[(aa['resname'] == 'HIS') & (aa['atname'].isin(('ND1','NE2','CE1','CG','CD2')))]
    elif resname == 'TRP':
      coor = aa[(aa['resname'] == 'TRP') & (aa['atname'].isin(('CD2','CE2','CE3','CH2','CZ2','CZ3')))]
    elif resname == 'TYR':
      coor = aa[(aa['resname'] == 'TYR') & ((aa['atname'].isin(('CG','CD1','CD2','CE1','CE2','CZ'))) | (aa['attype'] == 'C.ar'))]
    else:
      continue
    
    # Calculate center_of_mass of the amino-acid ring
    aa_center = center_of_mass(coor)
    aaringcenters[ring] = (plane_fit(coor[['xcoor','ycoor','zcoor']].values, center=aa_center))
  
  for pos_c in pcdist['source','atnum'].unique():
    ligatom = structure[structure['atnum'] == pos_c]
    ligatom_coor = coordinates(ligatom)
    
    for ring,data in aaringcenters.items():
      
      # Calculate distance between cation and ring center.
      # Calculate offset between ring center and cation projected onto ring plane
      pcdist = distance(ligatom_coor, data[0])
      pcoffset = distance(projection(data[1], data[0], ligatom_coor), data[0])
      
      if pcdist < pication_dist_max and pcoffset < pication_offset_max:
        
        # If it concerns an tertiary or quarternary amine. Check angles.
        # Otherwise, we might have have a pi-cation interaction 'through' the ligand
        a = None
        if ligatom['attype'].values[0] in ('N.3','N.4'):
          neigh = ligatom.neighbours(cutoff=1.6)
          nonhcount = neigh[neigh['attype'] != 'H'].shape[0]
          
          if nonhcount > 2:
            distdict = {}
            for idn,n in neigh.iterrows():
              distdict[distance(coordinates(n),data[0])] = n['atnum']
            closest = structure[structure['atnum'] == distdict[min(distdict.keys())]]
            
            # Is the amine neighbour closest to ring center a terminal one.
            # If not, check angles.
            closest_neigh = closest.neighbours(cutoff=1.6)
            if closest_neigh.shape[0] > 1:
              a = calc_angle(data[0], coordinates(closest), ligatom_coor)
              logger.debug("Charged ligand atom is amine: {0} bonded. Non-terminal bonded neighbour {1} closest to ring. Angle {2:.2f}".format(
                nonhcount, closest['atnum'].values[0], a))
              if a < pication_amine_angle_min:
                continue
           
        aa_ring = contact_frame[contact_frame['target','resnum'] == ring]
        logger.info("Cation-pi interaction between {0}-{1} and ring {2}-{3}. Distance: {4:.3f} Offset: {5:.2f}".format(
          ligatom['atname'].values[0], ligatom['atnum'].values[0], aa_ring['target','resname'].values[0],
          aa_ring['target','resnum'].values[0], pcdist, pcoffset))
        
        newindex = max(contact_frame.index)+1
        contact_frame.loc[newindex, 'contact'] = 'pc'
        contact_frame.loc[newindex,('target','distance')] = pcdist
        contact_frame.loc[newindex,('target','angle')] = a or numpy.nan
        for label in ['segid','chain','resname','resnum']:
          contact_frame.loc[newindex, ('target',label)] = aa_ring['target',label].unique()[0]
        contact_frame.loc[newindex, ('target','atname')] = 'X1'
        contact_frame.loc[newindex, ('target','attype')] = 'Du'
        contact_frame.loc[newindex, ('target','elem')] = 'D'
        
        #contact_frame.loc[newindex,('target','angle')] = a
        for label in ['segid','chain','resname','resnum','atname','atnum','elem','attype']:
          contact_frame.loc[newindex, ('source',label)] = ligatom[label].values[0]
  
  return contact_frame
  
def eval_pistacking(contact_frame, structure, rings=[], pistack_dist_max=7.5, pistack_ang_dev=30, pistack_offset_max=2.0):
  
  """
  Evaluate pi- and T-stacking between aromatic rings
  
  A pi- or T-stacking interaction is identified if the centers-of-mass of the two
  aromatic rings are within pistack_dist_max from each other; the offset distance
  between center-of-mass of one ring projected onto the other is no more than
  pistack_offset_max and if the angle between the normals of both rings does not
  deviate more than pistack_ang_dev from 180 deg for pi-stacking or 90+/-offset
  of T-stacking
  
  Identified pi- or T-stacking interactions are added to the contact_frame as 
  contact between the center-of-mass of the two rings represented by two dummy atoms
  Du, (element D) of residue X1. The target distance is the 3D euclidean distance 
  between the two dummy atoms and the target angle the smallest angle between the
  two ring normals. Pi-stacking contacts are marked 'ps' and T-stacking 'ts'
  
  :param contact_frame: LIEContactFrame
  :param structure: Pandas DataFrame representing the structure
  :param rings: Structure DataFrame index values of atoms that are part of ligand
                aromatic rings. A lists of lists
  :param pistack_dist_max: Cutoff distance between aromatic center-of-masses
  :param pistack_ang_dev: Maximum angle variation between ring normals. Deviation
                          from 180 for pi-stacking and 90 for T-stacking
  :param pistack_offset_max: Cutoff distance between center-of-masses projected
                             on top of each other.
  """
  
  if not len(rings):
    return contact_frame
  
  logger.debug("Run pi- or T-stacking detection on {0} ligand rings using: pistack_dist_max={1}, pistack_ang_dev={2}, pistack_offset_max={3}".format(
    len(rings), pistack_dist_max, pistack_ang_dev, pistack_offset_max))
  
  # Loop over aromatic rings of the ligand
  for ring in rings:
      
    # Get PHE, HIS, TRP or TYR residues pistack_dist_max away from any
    # aromatic atom
    aromatic = structure.loc[ring,:]
    neigh = aromatic.neighbours(cutoff=pistack_dist_max)
    neigh = neigh[neigh['resname'].isin(('PHE','HIS','TRP','TYR'))]
    
    if not neigh.empty:
      
      # Calculate center_of_mass of aromatic system
      aromatic_center = center_of_mass(aromatic)
      
      # Calculate normal to center of mass and place dummy atom 2A above normal
      aromatic_center, aromatic_norm = plane_fit(aromatic[['xcoor','ycoor','zcoor']].values, center=aromatic_center)
      
      for residue in neigh['resnum'].unique():
        aa = structure[structure['resnum'] == residue]
        resname = aa['resname'].unique()[0]
        aa_rings = []
        if resname == 'PHE':
          aa_rings.append(aa[(aa['resname'] == 'PHE') & ((aa['atname'].isin(('CG','CD1','CD2','CE1','CE2','CZ'))) | (aa['attype'] == 'C.ar'))])
        elif resname == 'HIS':
          aa_rings.append(aa[(aa['resname'] == 'HIS') & (aa['atname'].isin(('ND1','NE2','CE1','CG','CD2')))])
        elif resname == 'TRP':
          aa_rings.append(aa[(aa['resname'] == 'TRP') & (aa['atname'].isin(('CD2','CE2','CE3','CH2','CZ2','CZ3')))])
          aa_rings.append(aa[(aa['resname'] == 'TRP') & (aa['atname'].isin(('CD2','CE2','CG','NE1','CD1')))])
        elif resname == 'TYR':
          aa_rings.append(aa[(aa['resname'] == 'TYR') & ((aa['atname'].isin(('CG','CD1','CD2','CE1','CE2','CZ'))) | (aa['attype'] == 'C.ar'))])
        else:
          continue
        
        for coor in aa_rings:
          if coor.empty:
            continue
          
          # Calculate center_of_mass of the amino-acid ring
          aa_center = center_of_mass(coor)
        
          # Calculate normal to center of mass and place dummy atom 2A above normal
          aa_center, aa_norm = plane_fit(coor[['xcoor','ycoor','zcoor']].values, center=aa_center)
        
          # Calculate distance between ring centers
          dist = distance(aromatic_center, aa_center)
        
          # Evaluate aromatic center distance cutoff.
          if dist < pistack_dist_max:
          
            # Calculate ring offset, (project each ring center into the other ring)
            proj1 = projection(aromatic_norm, aromatic_center, aa_center)
            proj2 = projection(aa_norm, aa_center, aromatic_center)
            offset = min(distance(proj1, aromatic_center), distance(proj2, aa_center))
          
            stack = False
            a = angle(aromatic_norm, aa_norm, deg=True)
            a = min(a, 180-a if not 180-a < 0 else a)  # Smallest of two angles, depending on direction of normal
          
            # pi-stacking
            if 0 < a < pistack_ang_dev and offset < pistack_offset_max:
              logger.info("Pi-stacking between ring {0} and {1}-{2}. Distance: {3:.3f} Angle: {4:.2f} Offset: {5:.2f}".format(
                ring, residue, resname, dist, a, offset))
              stack = 'ps'
          
            # T-stacking
            elif 90-pistack_ang_dev < a < 90+pistack_ang_dev and offset < pistack_offset_max:
              logger.info("T-stacking between ring {0} and {1}-{2}. Distance: {3:.3f} Angle: {4:.2f} Offset: {5:.2f}".format(
                ring, residue, resname, dist, a, offset))
              stack = 'ts'

            if stack:
              
              # Remove any hydrofobic interactions if pi-stacking
              if stack == 'ps':
                logger.debug("Remove hydrofobic interaction label for all atoms in the pi-stacked ring")
                for ring_atom in ring:
                  if ring_atom in contact_frame.index:
                    contact_frame.loc[ring_atom,'contact'] = remove_contact_type(contact_frame.loc[ring_atom, 'contact'].values[0],'hf')
              
              newindex = max(contact_frame.index)+1
              contact_frame.loc[newindex, 'contact'] = stack
              contact_frame.loc[newindex,('target','distance')] = dist
              contact_frame.loc[newindex,('target','angle')] = a
              for label in ['segid','chain','resname','resnum']:
                contact_frame.loc[newindex, ('source',label)] = aromatic[label].unique()[0]
              contact_frame.loc[newindex, ('source','atname')] = 'X1'
              contact_frame.loc[newindex, ('source','attype')] = 'Du'
              contact_frame.loc[newindex, ('source','elem')] = 'D'
              for label in ['segid','chain','resname','resnum']:
                contact_frame.loc[newindex, ('target',label)] = aa[label].unique()[0]
              contact_frame.loc[newindex, ('target','atname')] = 'X1'
              contact_frame.loc[newindex, ('target','attype')] = 'Du'
              contact_frame.loc[newindex, ('target','elem')] = 'D'
              
  return contact_frame
            
def find_rings(structure, check_planar=True, check_aromatic=True, bond_cutoff=1.6, aromatic_planarity=7.5, maxiter=1000):
  
  """
  Find rings in the structure
  
  This function uses graph based cycle detection to find the
  set of smallest unique rings in the structure. The graph
  algorithm will return all rings in the system regardsless
  there nature. Optional filters can remove rings that are not
  planar and label rings as aromatic or non-aromatic based on
  there SYSBYL atom type.
  
  NOTE: The function return a dictionary of lists in which each
  list represent a ring. The integer values in the list are the
  index numbers of the structure DataFrame, not the atom numbers.
  
  PROBLEMS: Fused rings that form a 3D box are not wel recovered.
  Fused rings like estrogens always miss out on one ring, the
  aromatric ring is found.
  
  Algorithm:
  1) Select all heavy atoms in the system. attype != H
  2) Build the adjacency matrix using a default bond length
     cutoff of 1.6 A. Perform a check to see if the structure
     contains sulphur. Ajust the cutoff to 1.81 A.
  3) Construct a boolean matrix from the adjacency matrix to
     identify bonded neighbours (1) from non bonded ones (0).
  4) Iterativly remove all atoms having only one neighbour
  5) Build a graph representation from the boolean matrix with
     the atoms as nodes and covalently bonded neighbours as 
     edge list.
  6) Iterate over the nodes of the graph. for each node evaluate
     connectivity using depth-first search (dfs). Minimize number
     of recursions by keeping track of nodes already visited.
  7) Evaluate the spanning tree while it grows to see if there
     can be a path created back to the ancestor (cycle).
  8) For each ring (cycle) found, recreate the visited nodes
     dictionary only with the nodes having two connections.
     This prevents evaluating atoms that are part of a ring already
     found but still allow atoms that may be part of fused rings.
  9) Repeat setp 5 till 8 for a graph in which the neighbour list
     is reversed to evaluate connectivity in the opposite direction
     and minimize the changes of a deadlock.
  10) Filter the list of rings: remove duplicate rings, remove 
      fused rings for wich the individual members have also been 
      found (smallest set of smallest rings).
      If check_planar equals true, filter rings that are not planar.
  11) Construct list of rings found. Each list item is a tuple of 
      the ring list and a type label indicate nature of the rings as: 
      'RPA' = planar aromatic, 'RPN' = planar non-aromatic, 
      'RNA' = non-planar aromatic and 'RNN' = non-planar non-aromatic.
      
  :param structure: Pandas DataFrame representing the structure
  :param check_planar: Check for ring planarity. Label with 'P' or
                       'S' for planar or skewed respectivly.
  :param check_aromatic: Check for ring aromaticity. Label as 'A' or
                        'N' or aromatic or non-aromatic respectivly.
  :param bond_cutoff: Covalent bond cutoff length. Default 1.6 A.
  :param maxiter: Maximum number of iterations for the removal of
                  single bonded atoms. Default equals 1000.
  
  :return: list of ring atom index lists / type tuples.
  """
  
  # Get all heavy atoms of the system
  heavyatoms = structure[structure['attype'] != 'H']
  indexes = list(heavyatoms.index.values)
  
  # Filter the distance matrix on the heavy atoms and
  # select all create boolean marix for all entries 
  # with a distance below covalent bond cutoff
  # NOTE: can't use ._distance_matrix in heavyatoms selection. Misreferencing
  if 'S' in heavyatoms['atname'].unique():
    bond_cutoff = 1.81
    logger.debug("Detected sulphur in structure. Adjust covalent bond length cutoff to {0:.2f}".format(bond_cutoff))
      
  adjmatr = structure._distance_matrix.loc[indexes, indexes]
  boolmatr = adjmatr[(adjmatr > 0) & (adjmatr < bond_cutoff)].notnull().astype(int)
  logger.debug("{0} covalently linked heavy atoms in structure".format(adjmatr.shape[0]))
  
  # Remove all atoms with one neighbour. Keep on cycling till
  # there are non left.
  singles = True; itr = 0
  while singles and itr != maxiter:  
    onebond = boolmatr.loc[boolmatr.sum(axis=1) == 1]
    if not onebond.empty:
      indexes = set(boolmatr.index.values).difference(set(onebond.index.values))
      boolmatr = boolmatr.loc[indexes,indexes]
      itr += 1
    else:
      singles = False
  
  logger.debug("Removed {0} terminal, non-cyclic atoms in {1} iterations".format(adjmatr.shape[0] - boolmatr.shape[0], itr))
      
  def find_cycle_to_ancestor(node, ancestor):
    
    """
    Find a cycle containing both node and ancestor.
    """
    
    path = []
    while (node != ancestor):
      if (node is None):
        return []
      path.append(node)
      node = spanning_tree[node]
    path.append(node)
    path.reverse()
    
    return path
  
  def dfs(node):
      
    """
    Depth-first search subfunction.
    """
  
    visited[node] = len(graph[node])
    # Explore recursively the connected component
    for each in graph[node]:
      if (ring):
        return
      if (each not in visited):
        spanning_tree[each] = node
        dfs(each)
      else:
        if (spanning_tree[node] != each):
          ring.extend(find_cycle_to_ancestor(node, each))
          
  # Efficient ring detection using Depth-first search (dfs). 
  # Maintains a list of visited atoms to prevent revisit of atoms
  # having only two connections and previously found to be part of
  # a ring.
  rings = []
  for pathset in ('forward','reversed'):
    
    # Create a graph representation of the structure (atoms are nodes, bonds the edges)
    if pathset == 'forward': graph = dict([(ida,list(a[a == 1].index.values)) for ida,a in boolmatr.iterrows()])
    else: graph = dict([(ida,list(a[a == 1].index.values[::-1])) for ida,a in boolmatr.iterrows()])
    
    visited = {}; spanning_tree = {}
    subrings = []; ring = []
    for atom in graph.keys():
      # Select a non-visited node
      if (atom not in visited):
        spanning_tree[atom] = None
        dfs(atom) # Explore atom connections
        if (ring):
          subrings.append(ring)
          visited = dict([(a,2) for c in subrings for a in c if len(graph[a]) == 2])
          ring = [] # Reset cycle list
          
    rings.extend(subrings)
    
  if not rings:
    logger.debug("No rings found.")
    return []
  
  # Filter cycles list to remove duplicates but maintain cycle
  # linkage order.
  filtered_rings = []
  indexes = []
  for i,c in enumerate(rings):
    c = set(c)
    
    superset = False
    for r2 in rings:
      if c.issuperset(set(r2)) and len(c) > len(r2):
        logger.debug("Detected ring {0} superset of smaller rings. Remove".format(list(c)))
        superset = True
        break
    
    if not c in filtered_rings and not superset:
      filtered_rings.append(c)
      indexes.append(i)
  
  # Determine ring planarity and check for aromaticity
  ringlist = []
  for r in indexes:
    
    # Check planarity
    label = 'R'
    if check_planar:
      coor = structure.loc[rings[r], ['xcoor','ycoor','zcoor']]
      planar = True
      for n in itertools.combinations(coor.index, 4):
        dangle = dihedral(coor.loc[n[0],:].values, coor.loc[n[1],:].values, coor.loc[n[2],:].values, coor.loc[n[3],:].values)
        if 0 <= dangle <= aromatic_planarity or 180-aromatic_planarity <= dangle <= 180:
          continue
        else:
          planar = False
          logger.debug("Detected ring {0} not planar".format(rings[r]))
          break 
          
      if planar:
        label += 'P'
      else:
        label += 'S'
    
    # Check aromaticity
    if check_aromatic:
      attypes = list(structure.loc[rings[r], 'attype'].values)
      if (attypes.count('C.ar') + attypes.count('N.ar')) == len(attypes):
        label += 'A'
      else:
        label += 'N'
      
    ringlist.append((rings[r], label))
  
  return ringlist

class LIEContactFrame(LIEDataFrameBase):
  
  _class_name   = 'contact'
  _column_names = DEFAULT_CONTACT_COLUMN_NAMES
  
  def __init__(self, *args, **kwargs):
      
    super(LIEContactFrame, self).__init__(*args, **kwargs)
    
  @property
  def _constructor(self):
    
    return LIEContactFrame
  
  def _init_distance_matrix(self):
    
    # Create pair-wise distance matrix
    coords = self[['xcoor','ycoor','zcoor']]
    distances = pdist(coords.values)
    self._distance_matrix = DataFrame(squareform(distances))
    
  def append(self, other, ignore_index=True, verify_integrity=False):
    
    # Change atom numbering target to match self
    atnumend = self['atnum'].max() + 1
    renumber = range(atnumend, atnumend + len(other))
    other['atnum'] = renumber
    
    new = super(LIEContactFrame, self).append(other, ignore_index=ignore_index, verify_integrity=verify_integrity)
    new._metadata['parent'] = new
    
    # Recalculate distance matrix
    if '_distance_matrix' in new._metadata:
      del new._metadata['_distance_matrix']
      new._init_distance_matrix()
    
    return new
  
  def _get_elements(self):
    
    # Determine element types if not defined
    elements = cheminfo.loc[(cheminfo['type'] == 'atom') & (cheminfo['class'] == 'element'), 'name'].values
    for idx,atom in self.iterrows():
      if isnull(atom['elem']):
        a = atom['atname']
        if a in ('NA','NB','NE'): 
          self.loc[idx,'elem'] = 'N'
          continue
          
        if a in elements or a == atom['resname']:
          self.loc[idx,'elem'] = a
          continue
          
        a = re.sub('\d', '', a)
        self.loc[idx,'elem'] = a[0]
    
  def from_file(self, filepath, filetype='pdb', **kwargs):
    
    # Open the input regardless of its type using open_anything
    file_or_buffer = _open_anything(filepath)
    
    if filetype == 'pdb':
      
      # Init PDB parser class and parse PDB content
      pdb = PDBParser(file_or_buffer, columns=self._column_names.keys())
      structure_dict = pdb.parse()
                
    elif filetype == 'mol2':
      
      # Init MOL2 parser class and parse PDB content
      mol2 = MOL2Parser(file_or_buffer, columns=self._column_names.keys())
      structure_dict = mol2.parse()
      
    else:
      logger.error('Unknown filetype {0}'.format(filetype))
      return
    
    # Add structure data to dataframe
    if structure_dict:
      for col in structure_dict:
        if len(structure_dict[col]): self[col] = structure_dict[col]
    
    # Determine element types if not defined
    self._get_elements()
    
    # Create pair-wise distance matrix
    self._init_distance_matrix()
    
  def neighbours(self, target=None, cutoff=6.0):
    
    """
    Get all the neighbours of the current selection with respect to the full system
    or with resepct to another selection
    """
    
    # Get index of source (current selection) and target (full system without source) atoms
    source = set(self.index)
    if target:
      target = set(target.index).difference(source)
    else:
      target = set(self.parent.index).difference(source)
    
    # Get slice of contact matrix for source to target within cutoff distance
    contacts = self._distance_matrix.loc[target, source]
    contacts = contacts[contacts <= cutoff].dropna(how='all')
    
    return self.parent.loc[contacts.index, :]
  
  def contacts(self, target, columns=['segid','chain','resname','resnum','atname','atnum','attype','elem']):
    
    """
    Get the distance between the atoms in the current selection with respect to a target
    """
    
    # Get index of source (current selection) and target atoms
    source = set(self.index)
    target = set(target.index).difference(source)
    
    # Get slice of contact matrix representing the selection, reformat to row based Dataframe
    contacts = self._distance_matrix.loc[target, source]
    contacts = contacts.unstack().reset_index()
    contacts.index = range(len(contacts))
    contacts.columns = ['source','target','distance']
    
    # Get selection for source and target from parent, reindex and concatenate into new DataFrame
    source = self.parent.loc[contacts['source'].values, columns]
    source.index = range(len(source))
    target = self.parent.loc[contacts['target'].values, columns]
    target.index = range(len(target))
    
    contacts_frame = concat([source, target, contacts['distance']], axis=1)
    multi_index = [(['source']*len(columns) + ['target']*(len(columns)+1)), columns*2 + ['distance']]
    contacts_frame.columns = multi_index
    
    # Add angle column (for contacts with angle constraints)
    contacts_frame['target','angle'] = numpy.nan
    
    # Add a contact column and fill it with 'nd' (type not determined)
    contacts_frame['contact'] = 'nd'
    
    return contacts_frame
  
  def is_protein(self, tolerance=0.8):
    
    resnames = set(self['resname'].values)
    chemlookup = cheminfo.loc[(cheminfo['name'].isin(resnames)) & (cheminfo['type'] == 'residue'), 'class']
    chemlookup = list(chemlookup.values)
    
    if not chemlookup:
      return False
    elif len(set(chemlookup)) == 1 and len(chemlookup) == len(resnames) and 'aa' in chemlookup:
      return True
    elif 'aa' in chemlookup and chemlookup.count('aa') / float(len(chemlookup)) >= tolerance:
      logger.debug("Structure {0:.2f}% type protein but contains different residues ({1})".format(
        (chemlookup.count('aa') / float(len(chemlookup)))*100, set(chemlookup)))
      return True
    else:
      logger.debug("Structure of type {0}".format(set(chemlookup)))
      return False
  
  def is_ligand(self):
    
    if self.is_protein():
      return False
    
    resnames = set(self['resname'].values)
    if len(resnames.difference(set(METALS))) == 0:
      return False
    
    return True
    
    