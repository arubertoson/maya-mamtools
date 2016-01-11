"""
Outliner Sorting

Sort your outliner with more control than Mayas default methods.

.. todo::

    * make interface to decide ruleset
    * add options to include different sorting parameters
    * add functionality for hierarchy/selection sorting.

"""

import operator
import collections

import maya.cmds as cmds

import mampy


OutlinerItem = collections.namedtuple('OutlinerItem', 'name type')


def get_object_map():
    s = mampy.ls(assemblies=True)
    objects = collections.defaultdict(list)
    for obj in s.iterdags():
        shape = obj.get_shape()

        # Special cases for a "nicer" sort.
        if shape is None:
            objects['group'].append(OutlinerItem(obj.name, obj.typestr))
        else:
            if 'light' in shape.typestr.lower():
                objects['light'].append(OutlinerItem(obj.name, shape.typestr))
            else:
                objects[shape.typestr].append(OutlinerItem(obj.name, obj.typestr))
    return objects


def sort_keys(d, types):
    """Sort keys after names then given types."""
    d = sorted(d)
    for t in reversed(types):
        for idx, i in enumerate(d[::]):
            if i == t:
                item = d.pop(idx)
                d.append(item)
    return d


def outliner_sort():
    t = get_object_map()
    types = sort_keys(list(t.iterkeys()), ['camera', 'group'])

    for obj in types:
        s = sorted(t[obj], key=operator.attrgetter('type', 'name'), reverse=True)
        for i in s:
            cmds.reorder(i.name, f=True)


if __name__ == '__main__':
    outliner_sort()
