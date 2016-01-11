import logging
import collections

import maya.cmds as cmds
from maya.api.OpenMaya import MFn

import mampy

logger = logging.getLogger(__name__)


class WalkSelection(object):

    instance = None

    def __init__(self):

        self._pattern = None

        self._walkobject = WalkPattern()
        self.index = self._walkobject.current_index

    def __len__(self):
        try:
            return len(self.pattern)
        except TypeError:
            return 0

    @property
    def pattern(self):
        if self._pattern is None:
            self._pattern = self._walkobject.pattern
        return self._pattern

    def walk(self, backwards=False):
        index = self.index + (-1 if backwards else 1)

        if index == len(self) or index < -len(self):
            index = -1 if backwards else 0

        self.index = index

    def update(self):
        self.index = self.pattern.current_index()

    def next(self):
        self.walk()
        cmds.select(str(self.pattern[self.index]), add=True)

    def prev(self):
        self.walk(backwards=True)
        cmds.select(str(self.pattern[self.index+1]), d=True)


class WalkPattern(collections.Sequence):

    def __init__(self):
        self.elements = mampy.SelectionList()

        self._slist = None
        self._elist = None
        self._start_idx = None
        self._end_idx = None
        self._comp = None
        self._walklist = None
        self._pattern = None

        self.setup()

    def __getitem__(self, value):
        return self.pattern[value]

    def __len__(self):
        return len(self.pattern)

    @property
    def slist(self):
        if self._slist is None:
            self._slist = mampy.ordered_selection(-2)
            if not self._slist:
                raise TypeError('Invalid selection.')
        return self._slist

    @property
    def current_index(self):
        return self.walklist.index(self.end_idx)

    @property
    def comp(self):
        if self._comp is None:
            self._temp = mampy.SelectionList()
            self._temp.extend(self.slist)
            self._comp = self._temp[0]
        return self._comp

    @property
    def start_idx(self):
        if self._start_idx is None:
            self._start_idx = self.slist[0].index
        return self._start_idx

    @property
    def end_idx(self):
        if self._end_idx is None:
            self._end_idx = self.slist[1].index
        return self._end_idx

    @property
    def walklist(self):
        if self._walklist is None:
            try:
                self._walklist = list(self.elements[0].indices)
            except IndexError:
                logger.warn('self.elist is empty.')
        return self._walklist

    @walklist.setter
    def walklist(self, value):
        self._walklist = value

    @property
    def pattern(self):
        if self._pattern is None:
            self._pattern = mampy.SelectionList()
            for idx in self.walklist:
                new = self.comp.new()
                new.add(idx)
                self._pattern.append(new)
        return self._pattern

    def setup(self):
        self._create_elements()

        if (self.start_idx > self.end_idx and
                not self.end_idx == self.walklist[0]):
            self.walklist.reverse()
        self._slide_walklist()

        if not self.comp.type == MFn.kMeshEdgeComponent:
            difference = self.walklist.index(self.end_idx)
            self.walklist = self.walklist[::difference]

    def _slide_walklist(self):
        loop_deque = collections.deque(self.walklist)
        for i in self.walklist:
            current = loop_deque.popleft()
            if current == self.start_idx:
                loop_deque.appendleft(current)
                break
            loop_deque.append(current)
        self.walklist = list(loop_deque)

    def _create_elements(self):
        if (self.comp.type in [
            MFn.kMeshPolygonComponent,
            MFn.kMeshVertComponent,
                MFn.kMeshMapComponent]):
            if len(self.slist) == 1:
                raise ValueError('Unable to find loop from selection.')

            if not self.comp.type == MFn.kMeshMapComponent:
                loop = cmds.polySelectSp(list(self.slist), q=True, loop=True)
                loop = cmds.polySelectSp(loop, q=True, loop=True)
            else:
                loop = cmds.polySelect(
                    q=True, shortestEdgePathUV=self.comp.indices
                    )
                loop = cmds.polySelect(q=True, ass=True, euv=loop)
                loop = cmds.polyListComponentConversion(loop, tuv=True)
        elif self.comp.type == MFn.kMeshEdgeComponent:
            loop = cmds.polySelect(q=True, ass=True, rpt=self.comp.indices)
            if not loop:
                loop = cmds.polySelect(q=True, ass=True, lpt=self.comp.indices)

        self.elements.extend(loop)

    def update(self):
        return self.__class__()


if __name__ == '__main__':
    ws = WalkSelection()
    cmds.select(ws.pattern)
