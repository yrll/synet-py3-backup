#!/usr/bin/env python
"""
Synthesize configurations for eBGP protocol
"""

import copy
from collections import namedtuple
from enum import Enum

import z3

from synet.utils.mins import get_min_eval_select
from synet.utils.mins import get_max_eval_select


from synet.topo.bgp import Access
from synet.topo.bgp import ActionSetCommunity
from synet.topo.bgp import ActionSetLocalPref
from synet.topo.bgp import MatchCommunitiesList
from synet.topo.bgp import VALUENOTSET
from synet.topo.bgp import MatchLocalPref
from synet.topo.bgp import MatchPeer
from synet.topo.bgp import RouteMap
from synet.topo.bgp import MatchIpPrefixListList


__author__ = "Ahmed El-Hassany"
__email__ = "a.hassany@gmail.com"


z3.set_option('unsat-core', True)


class BGP_ATTRS_ORIGIN(Enum):
    """Enum of BGP origin types"""
    IGP = 1
    EBGP = 2
    INCOMPLETE = 3


SetDrop = namedtuple('DropRoute', ['value'])


"""
PREFIX: the prefix that's being announced
PEER: the peer from whom that prefix has been received
      (this is not technically in the BGP attributes set)
ORIGIN: See BGP_ATTRS_ORIGIN
ASPATH: List of AS numbers
NEXT_HOP:
    1. If the BGP Peers are in different AS then the NEXT_HOP IP address
       that will be sent in the update message will be the IP address of
       the advertising router.
    2. If the BGP peers are in the same AS (IBGP Peers),
        and the destination network being advertised in the update message
        is also in the same AS, then the NEXT_HOP IP address that will be sent
        in the update message will be the IP address of the advertising router
    3. If the BGP peers are in the same AS (IBGP Peers),
        and the destination network being advertised in the update message
        is in an external AS, then the NEXT_HOP IP address that will be
        sent in the update message will be the IP address of the external
        peer router which sent the advertisement to this AS.
LOCAL_PREF: is only used in updates sent to the IBGP Peers,
            It is not passed on to the BGP peers in other autonomous systems.
COMMUNITIES: List of Community values
"""
Announcement = namedtuple('Announcement', ['PREFIX', 'PEER', 'ORIGIN',
                                           'AS_PATH', 'NEXT_HOP',
                                           'LOCAL_PREF', 'COMMUNITIES'])
Imported = namedtuple('Imported', ['PREFIX', 'PEER', 'ORIGIN', 'AS_PATH',
                                   'NEXT_HOP', 'LOCAL_PREF', 'COMMUNITIES'])
Selected = namedtuple('Selected', ['PREFIX', 'PEER', 'ORIGIN', 'AS_PATH',
                                   'NEXT_HOP', 'LOCAL_PREF', 'COMMUNITIES'])
Exported = namedtuple('Exported', ['PREFIX', 'PEER', 'ORIGIN', 'AS_PATH',
                                   'NEXT_HOP', 'LOCAL_PREF', 'COMMUNITIES'])

RouteMapResult = namedtuple('RouteMapResult',
                            ['name', 'route_map', 'line', 'match_fun',
                             'match_synthesized', 'match_syn_map', 'action',
                             'action_val', 'localpref', 'communities',
                             'drop', 'smt', 'prev_result'])


class EBGP(object):
    """
    Synthesize configurations for eBGP protocol
    """
    def __init__(self, asnum, peer_name, nexthop, announcements,
                 all_communities, solver=None):
        """
        :param announcements: list of announcements received
        :param all_communities: a tuple of all the defined communities
        :param solver: optional instance of z3 solver
        """
        self.asnum = asnum
        self.peer_name = peer_name
        self.nexthop = nexthop
        self.solver = solver or z3.Solver()
        assert isinstance(announcements, dict)
        self.all_communities = all_communities
        c_mask = tuple(['F' for i in range(len(self.all_communities))])
        # The default "not valid" announcement
        # Used as helper in some SMT formulas
        self.notvalid = Announcement(PREFIX='NOTVALIDPREFIX',
                                     PEER='NOTVALIDPEER',
                                     ORIGIN=BGP_ATTRS_ORIGIN.EBGP,
                                     AS_PATH=[i for i in range(100)],
                                     NEXT_HOP='NOTVALIDNXTHOP',
                                     LOCAL_PREF=0,
                                     COMMUNITIES=c_mask)

        self.anns = announcements
        # Special none valid route to help with Z3 tricks!
        self.anns['notvalid'] = self.notvalid
        # Announcement Z3 type
        self.ann_sort = None
        # List of Z3 announcement objects
        self.all_announcements = None
        # Peer Z3 type
        self.peer_sort = None
        # List of Z3 peer objects
        self.all_peers = None
        # Prefix Z3 type
        self.perfix_sort = None
        # List of Z3 prefix objects
        self.all_prefixes = None
        # Announcement->Prefix
        self.prefix = None
        # Z3 Announcement->Peer
        self.peer = None
        # Z3 Announcement->LocalPref
        self.localpref = None
        # Z3 Announcement->AsPath Length
        self.aspathlength = None
        # Z3 Announcement-> True if Denied Routes
        self.route_denied = None
        # Z3 Communities
        self.communities = {}
        # Z3 Communities reverse map, takes z3 function name and return community
        self.reverse_communities = {}
        self.na_ann = None
        self._load_announcements()
        self.exported = {}

    def get_announcement(self, announcement_name):
        """Given a string name of the announcement return it's Z3 value"""
        return self._announcements_map[announcement_name]

    def get_not_valid_ann(self):
        """Return the Z3 variable for the special not valid announcement"""
        return self.get_announcement('notvalid')

    def get_peer(self, peer_name):
        """Given a string name of a peer return it's Z3 value"""
        return self._peers_map[peer_name]

    def get_prefix(self, prefix_name):
        """Given a string name of a prefix return it's Z3 value"""
        return self._prefixes_map[prefix_name]

    def _load_announcements(self):
        """
        Parse the given announcement list and initialize the various Z3 types
        :param announcements:
        :return: None
        """
        # Create Z3 Enum type for the announcements
        (self.ann_sort, all_announcements) = \
            z3.EnumSort('AnnouncementSort',
                        self.anns.keys())
        # Create Z3 Enum type for peers
        peers_list = list(set([ann.PEER for ann in self.anns.values()]))
        for a in peers_list:
            assert isinstance(a, basestring), "%s %s" % (a, type(a))
        (self.peer_sort, all_peers) = z3.EnumSort('PeerSort', peers_list)
        # Create Z3 Enum type for Prefixes
        anns_list = list(set([ann.PREFIX for ann in self.anns.values()]))
        (self.perfix_sort, all_prefixes) = z3.EnumSort('PrefixSort', anns_list)

        self.all_announcements = sorted(all_announcements)
        self.all_peers = sorted(all_peers)
        self.all_prefixes = sorted(all_prefixes)
        # For convenience
        ann_map = dict([(str(ann), ann) for ann in self.all_announcements])
        self._announcements_map = ann_map
        peer_map = dict([(str(peer), peer) for peer in self.all_peers])
        self._peers_map = peer_map
        prefixes_map = dict([(str(prefix), prefix) for prefix in self.all_prefixes])
        self._prefixes_map = prefixes_map
        self.na_ann = self.get_not_valid_ann()

        # Announcement Prefix
        self.prefix = z3.Function('Prefix', self.ann_sort, self.perfix_sort)
        # Announcement Peer
        self.peer = z3.Function('Peer', self.ann_sort, self.peer_sort)
        # LocalPref Function
        self.localpref = z3.Function('LocalPref', self.ann_sort, z3.IntSort())
        # AsPath Length
        self.aspathlength = z3.Function('ASPathLength', self.ann_sort, z3.IntSort())
        # Denied Routes
        self.route_denied = z3.Function('DeniedRoutes', self.ann_sort, z3.BoolSort())

        # Create functions for communities
        self.communities = {}
        for c in self.all_communities:
            name = 'Has_%s' % c
            self.communities[c] = z3.Function(name, self.ann_sort, z3.BoolSort())
            self.reverse_communities[name] = c

        # Feed the announcement info to the solver
        for i, name in enumerate(sorted(self.anns.keys())):
            ann = self.anns[name]
            var = self.get_announcement(name)
            # Set Prefix
            name = 'init_prefix_%s' % str(var)
            constraint = self.prefix(var) == self.get_prefix(ann.PREFIX)
            self.solver.assert_and_track(constraint, name)
            # Set Peer
            name = 'init_peer_%s' % str(var)
            constraint = self.peer(var) == self.get_peer(ann.PEER)
            self.solver.assert_and_track(constraint, name)
            # Set AS PATH LENGTH, TODO: Set AS PATH it self!
            name = 'init_as_path_length_%s' % str(var)
            constraint = self.aspathlength(var) == len(ann.AS_PATH)
            self.solver.assert_and_track(constraint, name)
            # Set LOCAL PREF
            if ann.LOCAL_PREF == '?':
                self.solver.add(self.localpref(var) > 0)
            else:
                name = 'init_local_pref_%s' % str(var)
                constraint = self.localpref(var) == ann.LOCAL_PREF
                self.solver.assert_and_track(constraint, name)
            # Nothing denied, only route maps can do that
            self.solver.add(self.route_denied(var) == False)

            # Assign communities
            for i, c in enumerate(ann.COMMUNITIES):
                c_name = self.all_communities[i]
                c_fun = self.communities[c_name]
                assert_name = 'init_comm_%s_%s' % (str(var), c_name)
                if c == 'T':
                    self.solver.assert_and_track(c_fun(var) == True, assert_name)
                elif c == 'F':
                    self.solver.assert_and_track(c_fun(var) == False, assert_name)

    def _get_communities_match(self, name, match, prev_communities):
        """
        Given a MatchCommunity, return a Z3 function and list of constraints
        for the synthesis.
        :param name: The name of this route map
        :param match: MatchCommunity
        :param prev_communities: dict of previous communities
        :return:
        """
        assert isinstance(match, MatchCommunitiesList)
        communities = match.match.communities
        assert len(communities) == 1, "Only only community per list is supported"
        match_synthesized = None
        match_syn_map = None
        if communities != [VALUENOTSET]:
            constraints = []
            match_fun = prev_communities[communities[0]]
        else:
            # This is a bit tricky to handle
            # In case the community match is EMPTY,
            #     the the synthesizer is free to choose any community
            # We create a dummy function such that it ranges and values maps exactly to
            # one or more assigned communities.
            # Then we enumerate the communities,
            # and the variable _Selected_Community tells us which one that successfully
            # mapped to our dummy match
            f_name = '%s_Synthesize_Comm_Match' % name
            dummy_match = z3.Function(f_name, self.ann_sort, z3.BoolSort())
            c_name = '%s_Selected_Comm_Match' % name
            match_synthesized = z3.Const(c_name, z3.IntSort())
            match_syn_map = {}
            constrains = []
            for i, community in enumerate(sorted(prev_communities.keys())):
                t1 = z3.Const('%s_Tmp%d' % (name, i), self.ann_sort)
                match_syn_map[i] = prev_communities[community]
                constrains.append(
                    z3.And(match_synthesized == i,
                           z3.ForAll(
                               [t1],
                               dummy_match(t1) == prev_communities[community](t1)
                           ))
                )
            constraints = [z3.Or(*constrains)]
            #self.solver.append(constrains)
            match_fun = dummy_match
        return match_fun, match_synthesized, match_syn_map, constraints

    def _get_localpref_match(self, name, match, prev_localpref):
        """
        Given a MatchLocalPref, return a Z3 function and list of constraints
        for the synthesis.
        :param name: The name of this route map
        :param match: MatchLocalPref
        :param prev_localpref:
        :return:
        """
        assert isinstance(match, MatchLocalPref)
        if match.match != VALUENOTSET:
            match_fun = lambda x: prev_localpref(x) == match.match
        else:
            t1, t2 = z3.Consts('%s_Tmp1 %s_Tmp2' % (name, name), self.ann_sort)
            f_name = '%s_Synthesize_LocalPref_Match' % (name)
            dummy_match = z3.Function(f_name, self.ann_sort, z3.IntSort())
            c_name = '%s_Selected_LocalPref_Match' % (name)
            match_synthesized = z3.Const(c_name, z3.IntSort())
            match_syn_map = None
            self.solver.append(
                z3.ForAll(
                    [t1],
                    dummy_match(t1) == z3.If(prev_localpref(t1) == match_synthesized, True, False))
            )
            match_fun = dummy_match

        return match_fun, constraints

    def process_route_map(self, route_map, line, prev_localpref,
                          prev_communities, prev_drop, prev_result=None):
        """
        Process a RouteMap and return RouteMapResult
        :param route_map: instance of RouteMap
        :param prev_localpref:
        :param prev_communities:
        :param prev_drop:
        :param prev_result:
        :return:
        """
        name = "%s_%d" % (route_map.name, line.lineno)
        assert len(line.matches) == 1, "Only one match per line is supported"
        assert len(line.actions) in [0, 1], "Only one action per line is supported"
        match = line.matches[0]
        if len(line.actions) == 1:
            action = line.actions[0]
        else:
            assert line.access in [VALUENOTSET, Access.deny, Access.permit]
            if line.access == Access.permit:
                action = SetDrop(False)
            elif line.access == Access.deny:
                action = SetDrop(True)
            else:
                action = SetDrop(VALUENOTSET)
        # Temp variables for the quantifiers
        t1, t2 = z3.Consts('%s_Tmp1 %s_Tmp2' % (name, name), self.ann_sort)

        # The match part of the route map
        match_synthesized = None
        match_syn_map = None
        # Capture the match function, should be a boolean function
        if isinstance(match, MatchCommunitiesList):
            match_fun, match_synthesized, match_syn_map, constraints = self._get_communities_match(name, match, prev_communities)
            for constraint in constraints:
                self.solver.append(constraint)
        elif isinstance(match, MatchLocalPref):
            if match.match != VALUENOTSET:
                match_fun = lambda x: prev_localpref(x) == match.match
            else:
                t1, t2 = z3.Consts('%s_Tmp1 %s_Tmp2' % (name, name), self.ann_sort)
                f_name = '%s_Synthesize_LocalPref_Match' % (name)
                dummy_match = z3.Function(f_name, self.ann_sort, z3.IntSort())
                c_name = '%s_Selected_LocalPref_Match' % (name)
                match_synthesized = z3.Const(c_name, z3.IntSort())
                match_syn_map = None
                self.solver.append(
                    z3.ForAll(
                        [t1],
                        dummy_match(t1) == z3.If(prev_localpref(t1) == match_synthesized, True, False))
                )
                match_fun = dummy_match
        elif isinstance(match, MatchPeer):
            if match.match != VALUENOTSET:
                match_fun = lambda x: self.peer(x) == self.get_peer(match.match)
            else:
                dummy_match = z3.Function('%s_Synthesize_Peer_Match' % (name), self.ann_sort, z3.BoolSort())
                match_synthesized = z3.Const('%s_Selected_Peer_Match' % (name), self.peer_sort)
                match_syn_map = None
                self.solver.append(z3.ForAll([t1], dummy_match(t1) == z3.If(self.peer(t1) == match_synthesized, True, False)))
                match_fun = dummy_match
        elif isinstance(match, MatchIpPrefixListList):
            assert len(match.match.networks) == 1, "Only one prefix supported"
            if match.match.networks != [VALUENOTSET]:
                match_fun = lambda x: self.prefix(x) == self.get_prefix(match.match.networks[0])
            else:
                dummy_match = z3.Function('%s_Synthesize_Prefix_Match' % name, self.ann_sort, z3.BoolSort())
                match_synthesized = z3.Const('%s_Selected_Prefix_Match' % (name), z3.IntSort())
                match_syn_map = {}
                constrains = []
                for i, prefix in enumerate(sorted(self._prefixes_map.values())):
                    match_syn_map[i] = prefix
                    constrains.append(
                        z3.And(match_synthesized == i,
                               z3.ForAll([t1], dummy_match(t1) == z3.If(self.prefix(t1) == prefix, True, False)))
                    )
                constrains = z3.Or(*constrains)
                self.solver.append(constrains)
                match_fun = dummy_match
        else:
            raise ValueError("Unknown match type %s" % type(match))

        # Handle actions
        if line.access == Access.deny:
            # Function for denied routes
            route_denied = z3.Function('%s_DeniedRoutes' % (name,), self.ann_sort, z3.BoolSort())
            action_fun = route_denied
            action_val = z3.Const('%s_action_val' % name, z3.BoolSort())
            # If match then drop route, no further eval is needed
            c = z3.ForAll(
                [t1],
                z3.If(match_fun(t1) == True,
                      route_denied(t1) == action_val,
                      route_denied(t1) == prev_drop(t1)))
            c = z3.And(c, action_val == True)
            result_communities = prev_communities
            result_localpref = prev_localpref
            result_drop = route_denied
            result_smt = c
        elif isinstance(action, ActionSetLocalPref):
            newlocalpref = z3.Function('%s_localPref' % name, self.ann_sort, z3.IntSort())
            action_fun = newlocalpref
            action_val = z3.Const('%s_action_val' % name, z3.IntSort())
            # If local pref is not fixed, then leave it empty for the SMT to assign
            c = z3.ForAll([t1], newlocalpref(t1) == z3.If(match_fun(t1) == True, action_val, prev_localpref(t1)))
            if action.value != VALUENOTSET:
                c = z3.And(c, action_val == action.value)
            else:
                c = z3.And(c, action_val > 0)
            # If the route already dropped, then don't bother
            with_drop = z3.ForAll([t1], z3.Implies(prev_drop(t1) == False, c))
            result_communities = prev_communities
            result_localpref = newlocalpref
            result_drop = prev_drop
            result_smt = with_drop
        elif isinstance(action, ActionSetCommunity):
            newcommunity = z3.Function('%s_Has%s' % (name, action.community), self.ann_sort, z3.BoolSort())
            action_fun = newcommunity
            action_val = z3.Const('%s_action_val' % name, z3.BoolSort())
            c = z3.ForAll([t1], newcommunity(t1) == z3.If(match_fun(t1), action_val, prev_communities[action.community](t1)))
            if action.value != EMPTY:
                c = z3.And(c, action_val == action.value)
            result_communities = prev_communities.copy()
            result_communities[action.community] = newcommunity
            result_localpref = prev_localpref
            result_drop = prev_drop
            result_smt = c
        elif isinstance(action, SetDrop):
            # Function for denied routes
            route_denied = z3.Function('%s_DeniedRoutes' % name, self.ann_sort, z3.BoolSort())
            action_fun = route_denied
            action_val = z3.Const('%s_action_val' % name, z3.BoolSort())
            c = z3.ForAll(
                [t1],
                route_denied(t1) == z3.If(
                    match_fun(t1) == True,
                    action_val,
                    prev_drop(t1)))
            if action.value != VALUENOTSET:
                c = z3.And(c, action_val == action.value)
            result_communities = prev_communities
            result_localpref = prev_localpref
            result_drop = route_denied
            result_smt = c

        # Prepare our results
        result = RouteMapResult(name, route_map=route_map, line=line, match_fun=match_fun, match_synthesized=match_synthesized,
                                match_syn_map=match_syn_map, action=action_fun, action_val=action_val,
                                communities=result_communities, localpref=result_localpref, drop=result_drop,
                                smt=result_smt, prev_result=prev_result)
        return result

    def process_route_maps(self, route_maps):
        """
        Iterate through the lines of the given route map with holes
        :param route_map: RouteMap as part of requirement
        :return: RouteMapResult of the last route map in the list
        """
        if len(route_maps.lines) == 0:
            result = RouteMapResult(
                'EmptyRouteMap', route_map=None, line=None, match_fun=None,
                match_synthesized=None, match_syn_map=None, action=None,
                action_val=None, communities=self.communities,
                localpref=self.localpref, drop=self.route_denied,
                smt=None, prev_result=None)
            return result
        first = route_maps.lines[0]
        result = self.process_route_map(
            route_map=route_maps, line=first, prev_communities=self.communities,
            prev_localpref=self.localpref, prev_drop=self.route_denied,
            prev_result=None)
        name = 'route_map_%d_%s' % (first.lineno, route_maps.name)
        self.solver.assert_and_track(result.smt, name)
        prev_result = result
        for line in route_maps.lines[1:]:
            result = self.process_route_map(
                route_map=route_maps, line=line, prev_communities=prev_result.communities,
                prev_localpref=prev_result.localpref,
                prev_drop=prev_result.drop, prev_result=prev_result)
            name = 'route_map_%d_%s' % (line.lineno, route_maps.name)
            self.solver.assert_and_track(result.smt, name)
            prev_result = result
        return prev_result

    def eval_route_map(self, model, result, summary=True):
        lines = []
        if result.prev_result is not None:
            lines.extend(self.eval_route_map(model, result.prev_result, summary))
        name = result.name
        if result.route_map is None:
            return []
        print "\tRoute Map", name

        # Create a copy to maintain the original route map with holes
        line = copy.deepcopy(result.line)

        if result.match_synthesized is None:
            matches = line.matches
            print "\t\t", "Match", matches
            val = model.eval(result.action_val)
            print "\t\t", "Action", result.action, val
        else:
            if result.match_syn_map:
                synthesize_match = result.match_syn_map[model.eval(result.match_synthesized).as_long()]
                name = str(synthesize_match)
                if str(result.match_synthesized).endswith('Selected_Prefix_Match'):
                    line.matches[0].match.networks = [name]
                elif name.startswith('Has_Community'):
                    comm = self.reverse_communities[name]
                    line.matches[0].match.communities = [comm]
                else:
                    raise Exception("Unknown function name %s" % name)
            else:
                synthesize_match = model.eval(result.match_synthesized)
                synthesize_match = str(synthesize_match)
                try:
                    synthesize_match = int(synthesize_match)
                except:
                    pass
                line.matches[0].match = synthesize_match

            print "\t\t", "Match (S)", line.matches, synthesize_match
            print "\t\t", "Action", result.action, model.eval(result.action_val)

        if str(result.action).endswith('DeniedRoutes') and line.access == VALUENOTSET:
            val = model.eval(result.action_val)
            if z3.is_true(val):
                line.access = Access.deny
            else:
                line.access = Access.permit

        #for route in self._announcements_map.values():
        #     if str(route) == 'Ann0': continue
        #     print "\t\t", result.match, route, model.eval(result.match(route))
        #     print "\t\t", result.action, route, model.eval(result.action(route))
        return lines + [line]

    def solve(self, route_maps, required_names=[]):
        na = self.get_not_valid_ann()
        result = self.process_route_maps(route_maps)

        localpref_fun = result.localpref
        communities_fun = result.communities
        route_denied = result.drop
        select_route_vars = []
        for prefix in set([ann.PREFIX for ann in self.anns.values()]):
            if prefix == self.notvalid.PREFIX:
                continue
            Selected = z3.Const('SelectedRoute%s' % prefix, self.ann_sort)
            select_route_vars.append(Selected)
            prefixAnn = [self.get_announcement(ann) for ann in self._announcements_map if self.anns[ann].PREFIX == prefix]
            if len(prefixAnn) == 1:
                self.solver.assert_and_track(Selected == z3.If(route_denied(prefixAnn[0]), na, prefixAnn[0]), 'direct_%s' % prefix)
            else:
                MaxLP = z3.Const('MaxLP%s' % prefix, z3.IntSort())
                MinAS = z3.Const('MinAS%s' % prefix, z3.IntSort())
                # Find the maximum local pref
                self.solver.add(MaxLP == localpref_fun(get_max_eval_select(route_denied, False, localpref_fun, na, *prefixAnn)))
                self.solver.add(Selected == get_min_eval_select(localpref_fun, MaxLP, self.aspathlength, na, *prefixAnn))

            for name in required_names:
                if prefix == self.anns[name].PREFIX:
                    n = 'select_%s_%s' % (prefix, name)
                    self.solver.assert_and_track(
                        Selected == self.get_announcement(name), n)

        if self.solver.check() == z3.sat:
            model = self.solver.model()
            selected_routes = []
            for route in select_route_vars:
                route = str(model.eval(route))
                # Skip the non valid route
                if route == 'notvalid': continue
                selected_routes.append(route)

            lines = self.eval_route_map(model, result)
            self.synthesized_route_map = RouteMap(route_maps.name, lines)
            #for name in sorted(self._announcements_map.keys()):
            #    ann = self.get_announcement(name)
            #   print "Drop", route_denied, name, model.eval(route_denied(ann))
            #assert set(selected_routes) == set(required_names), "Selected Routes are %s and required are %s" % (selected_routes, required_names)
            self.exported = {}
            for var in select_route_vars:
                ann_name = str(model.eval(var))
                if ann_name == 'notvalid': continue
                ann = self.anns[ann_name]
                prefix = ann.PREFIX
                peer = ann.PEER
                origin = ann.ORIGIN
                as_path = ann.AS_PATH
                next_hop = ann.NEXT_HOP
                localpref = model.eval(localpref_fun(var)).as_long()
                comms = []
                for comm in self.all_communities:
                    comms.append('T' if z3.is_true(model.eval(communities_fun[comm](var))) else 'F')
                communities = tuple(comms)
                new_ann = Announcement(PREFIX=prefix, PEER=self.peer_name, ORIGIN=origin, AS_PATH=[self.asnum] + as_path,
                                       NEXT_HOP=self.nexthop, LOCAL_PREF=localpref, COMMUNITIES=communities)
                self.exported[ann_name] = new_ann

            #print self.solver.to_smt2()
            #print model
            return True
        else:
            print self.solver.unsat_core()
            return False