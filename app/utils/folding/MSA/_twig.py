"""
Hui Modified Version of phylogenetic tree implementation. from Bio package.
1. add __getitem__ method for BaseTree
2. add quick _get_terminal method
3. add clades method to BaseTree, so tree can be treated as clade.
4. add quick _get_children method to list all children of a given clade.
5. add give clades a parent property for future tracking of clade parent.
6. eliminate unwated feature in tree search: 8 times faster.
"""
import collections
import copy
import matplotlib.pyplot as plt
import matplotlib.collections as mpcollections

# General tree-traversal algorithms



def _level_traverse(root, get_children):
    """Traverse a tree in breadth-first (level) order (PRIVATE)."""
    Q = collections.deque([root])
    while Q:
        v = Q.popleft()
        yield v
        Q.extend(get_children(v))


def _preorder_traverse(root, get_children):
    """Traverse a tree in depth-first pre-order (parent before children) (PRIVATE)."""
    def dfs(elem):
        yield elem
        for v in get_children(elem):
            for u in dfs(v):
                yield u
    for elem in dfs(root):
        yield elem


def _postorder_traverse(root, get_children):
    """Traverse a tree in depth-first post-order (children before parent) (PRIVATE)."""
    def dfs(elem):
        for v in get_children(elem):
            for u in dfs(v):
                yield u
        yield elem
    for elem in dfs(root):
        yield elem

# Class definitions

class TreeElement(object):

    def __repr__(self):
        """Show this object's constructor with its primitive arguments."""
        return '{}(name={})'.format(self.__class__.__name__,self.name)

    __str__ = __repr__


class TreeMixin(object):
    # Traversal methods
    def __getitem__(self,slice):
        return self.find_elements(target=slice)

    def find_elements(self, target=None,order='level'):
        """
        return the clade match target name.
        """
        order_opts = {'preorder': _preorder_traverse,
                      'postorder': _postorder_traverse,
                      'level': _level_traverse}
        order_func = order_opts[order]
        get_children = lambda elem: elem.clades
        root = self.root
        if target:
            for i in order_func(root,get_children):
                if target == i.name:
                    return i
        else:
            return order_func(root,get_children)

    def find_clades(self,order='level'):
        """
        return iterable of all tree clades.
        """
        return self.find_elements(target=None,order=order)

    def get_path(self, target=None, **kwargs):
        """List the clades directly between this root and the given target.

        :returns: list of all clade objects along this path, ending with the
            given target, but excluding the root clade.

        """
        # Only one path will work -- ignore weights and visits
        path = []
        def check_in_path(v):
            if v.name==target:
                path.append(v)
                return True
            elif v.is_terminal():
                return False
            for child in v:
                if check_in_path(child):
                    path.append(v)
                    return True
            return False
        if not check_in_path(self.root):
            return None
        return path[-2::-1]

    def _get_terminals(self,target=None):
        """
        return a list of terminals; much faster than get_terminals.
        """
        result = []
        def trace(tree,result):
            a = tree.clades
            if a:
                for i in a:
                    trace(i,result)
            else:
                result.append(tree.root.name)
        if target:
            tree = self[target]
        else:
            tree = self
        trace(tree,result)
        return result

    def _get_children(self,target=None):
        """
        return a list of all children name of a target
        """
        result = []
        def trace(tree,result):
            a = tree.clades
            if a:
                for i in a:
                    result.append(i.root.name)
                    trace(i,result)
        if target:
            tree = self[target]
        else:
            tree = self
        trace(tree,result)
        return result

    def _get_parent(self,target=None):
        """
        return the direct parent of an target.
        """
        c = self[target]
        if c.__dict__.get('parent',False):
            return c.parent
        else:
            p=self.get_path(target)
            return  p[-2] if len(p)>1 else self.root

    def get_terminals(self, target=None,order='preorder'):
        """Get a list of all of this tree's terminal (leaf) nodes."""
        result = []
        def trace(tree,result):
            a = tree.clades
            if a:
                for i in a:
                    trace(i,result)
            else:
                result.append(tree.root)
        if target:
            tree = self[target]
        else:
            tree = self
        trace(tree,result)
        return result

    def trace(self, start, finish):
        """List of all clade object between two targets in this tree.

        Excluding `start`, including `finish`.
        """
        mrca = self.common_ancestor(start, finish)
        fromstart = mrca.get_path(start)[-2::-1]
        to = mrca.get_path(finish)
        return fromstart + [mrca] + to

    # Information methods

    def common_ancestor(self, *targets):
        """Most recent common ancestor (clade) of all the given targets.

        Edge cases:
         - If no target is given, returns self.root
         - If 1 target is given, returns the target
         - If any target is not found in this tree, raises a ValueError

        """
        paths = [self.get_path(t)  for t in targets]
        # Validation -- otherwise izip throws a spooky error below
        for p, t in zip(paths, targets):
            if p is None:
                raise ValueError("target %s is not in this tree" % repr(t))
        mrca = self.root
        for level in zip(*paths):
            ref = level[0]
            for other in level[1:]:
                if ref is not other:
                    break
            else:
                mrca = ref
            if ref is not mrca:
                break
        return mrca

    def count_terminals(self):
        """Count the number of terminal (leaf) nodes within this tree."""
        return len(self._get_terminals())

    def depths(self, unit_branch_lengths=False):  # noqa: D402
        """Create a mapping of tree clades to depths (by branch length).

        :Parameters:
            unit_branch_lengths : bool
                If True, count only the number of branches (levels in the tree).
                By default the distance is the cumulative branch length leading
                to the clade.

        :returns: dict of {clade: depth}, where keys are all of the Clade
            instances in the tree, and values are the distance from the root to
            each clade (including terminals).

        """
        if unit_branch_lengths:
            depth_of = lambda c: 1
        else:
            depth_of = lambda c: c.branch_length or 0
        depths = {}

        def update_depths(node, curr_depth):
            depths[node] = curr_depth
            for child in node.clades:
                new_depth = curr_depth + depth_of(child)
                update_depths(child, new_depth)

        update_depths(self.root, self.root.branch_length or 0)
        return depths

    def distance(self, target1, target2=None):
        """Calculate the sum of the branch lengths between two targets.

        If only one target is specified, the other is the root of this tree.
        """
        if target2 is None:
            return sum(n.branch_length for n in self.get_path(target1)
                       if n.branch_length is not None)
        mrca = self.common_ancestor(target1, target2)
        return mrca.distance(target1) + mrca.distance(target2)

    def is_parent_of(self, target=None, **kwargs):
        """Check if target is a descendent of this tree.

        Not required to be a direct descendent.

        To check only direct descendents of a clade, simply use list membership
        testing: ``if subclade in clade: ...``
        """
        return self.get_path(target, **kwargs) is not None

    def is_preterminal(self):
        """Check if all direct descendents are terminal."""
        if self.root.is_terminal():
            return False
        for clade in self.root.clades:
            if not clade.is_terminal():
                return False
        return True

    # Tree manipulation methods

    def ladderize(self, reverse=False,sort_func=lambda c: c.count_terminals()):
        """Sort clades in-place according to the number of terminal nodes.

        Deepest clades are last by default. Use ``reverse=True`` to sort clades
        deepest-to-shallowest.
        """
        self.root.clades.sort(key=sort_func,
                              reverse=reverse)
        for subclade in self.root.clades:
            subclade.ladderize(reverse=reverse,sort_func=sort_func)

    def prune(self, target=None, **kwargs):
        """Prunes a terminal clade from the tree.

        If taxon is from a bifurcation, the connecting node will be collapsed
        and its branch length added to remaining terminal node. This might be no
        longer be a meaningful value.

        :returns: parent clade of the pruned target

        """
        if 'terminal' in kwargs and kwargs['terminal']:
            raise ValueError("target must be terminal")
        path = self.get_path(target, terminal=True, **kwargs)
        if not path:
            raise ValueError("can't find a matching target below this root")
        if len(path) == 1:
            parent = self.root
        else:
            parent = path[-2]
        parent.clades.remove(path[-1])
        if len(parent) == 1:
            # We deleted a branch from a bifurcation
            if parent == self.root:
                # If we're at the root, move the root upwards
                # NB: This loses the length of the original branch
                newroot = parent.clades[0]
                newroot.branch_length = None
                parent = self.root = newroot
            else:
                # If we're not at the root, collapse this parent
                child = parent.clades[0]
                if child.branch_length is not None:
                    child.branch_length += (parent.branch_length or 0.0)
                if len(path) < 3:
                    grandparent = self.root
                else:
                    grandparent = path[-3]
                # Replace parent with child at the same place in grandparent
                index = grandparent.clades.index(parent)
                grandparent.clades.pop(index)
                grandparent.clades.insert(index, child)
                parent = grandparent
        return parent



class Tree(TreeElement, TreeMixin):
    """A phylogenetic tree, containing global info for the phylogeny.

    The structure and node-specific data is accessible through the 'root'
    clade attached to the Tree instance.

    :Parameters:
        root : Clade
            The starting node of the tree. If the tree is rooted, this will
            usually be the root node.
        rooted : bool
            Whether or not the tree is rooted. By default, a tree is assumed to
            be rooted.
        id : str
            The identifier of the tree, if there is one.
        name : str
            The name of the tree, in essence a label.

    """

    def __init__(self, root=None, rooted=True, id=None, name=None):
        """Initialize parameter for phylogenetic tree."""
        self.root = root or Clade()
        self.rooted = rooted
        self.id = id
        self.name = name

    def __repr__(self):
        if self.name:
            return self.name
        return self.__class__.__name__



    @classmethod
    def from_clade(cls, clade, **kwargs):
        """Create a new Tree object given a clade.

        Keyword arguments are the usual `Tree` constructor parameters.
        """
        root = copy.deepcopy(clade)
        return cls(root, **kwargs)

    @property
    def clade(self):
        """Return first clade in this tree (not itself)."""
        return self.root

    @property
    def clades(self):
        """Return first clade in this tree (not itself)."""
        return [self.root]


    # Method assumed by TreeMixin

    def is_terminal(self):
        """Check if the root of this tree is terminal."""
        return (not self.root.clades)

    # Convention from SeqRecord and Alignment classes

    def __format__(self):
        return str(self)
    # Pretty-printer for the entire tree hierarchy

    def __str__(self):
        """Return a string representation of the entire tree.

        Serialize each sub-clade recursively using ``repr`` to create a summary
        of the object structure.
        """
        TAB = '    '
        textlines = []

        def print_tree(obj, indent):
            """Recursively serialize sub-elements.

            This closes over textlines and modifies it in-place.
            """
            if isinstance(obj, (Tree, Clade)):
                # Avoid infinite recursion or special formatting from str()
                objstr = repr(obj)
            else:
                objstr = repr(obj)
            textlines.append(TAB * indent + objstr)
            indent += 1
            for attr in obj.__dict__:
                child = getattr(obj, attr)
                if isinstance(child, TreeElement) and attr!='parent':
                    print_tree(child, indent)
                elif isinstance(child, list):
                    for elem in child:
                        if isinstance(elem, TreeElement):
                            print_tree(elem, indent)

        print_tree(self, 0)
        return '\n'.join(textlines)


class Clade(TreeElement, TreeMixin):
    """A recursively defined sub-tree.

    :Parameters:
        branch_length : str
            The length of the branch leading to the root node of this clade.
        name : str
            The clade's name (a label).
        clades : list
            Sub-trees rooted directly under this tree's root.
        confidence : number
            Support.
        color : BranchColor
            The display color of the branch and descendents.
        width : number
            The display width of the branch and descendents.

    """

    def __init__(self, branch_length=None, name=None, clades=None,
                 confidence=None, color=None, width=None):
        """Define parameters for the Clade tree."""
        self.branch_length = branch_length
        self.name = name
        self.clades = clades or []
        self.confidence = confidence
        self.color = color
        self.width = width
        self.parent = None

    @property
    def root(self):
        """Allow TreeMixin methods to traverse clades properly."""
        return self

    def is_terminal(self):
        """Check if this is a terminal (leaf) node."""
        return (not self.clades)

    # Sequence-type behavior methods

    def __iter__(self):
        """Iterate through this tree's direct descendent clades (sub-trees)."""
        return iter(self.clades)

    def __len__(self):
        """Return the number of clades directy under the root."""
        return len(self.clades)

    # Python 3:
    def __bool__(self):
        """Boolean value of an instance of this class (True).

        NB: If this method is not defined, but ``__len__``  is, then the object
        is considered true if the result of ``__len__()`` is nonzero. We want
        Clade instances to always be considered True.
        """
        return True

    def __str__(self):
        """Return name of the class instance."""
        if self.name:
            return self.name
        return self.__class__.__name__



#### function to draw tree
#draw(p, do_show=not save, save=save,
     # label_func=wrap(self, label), size=size,label_colors=colormap,colorbar=True if colormap else False)
def draw(tree, label_func=str, do_show=True,label_colors=None,save=False,colorbar=False,*args, **kwargs):

    # Arrays that store lines for the plot of clades
    horizontal_linecollections = []
    vertical_linecollections = []
    labelfontsize = 12- min(6,int(tree.count_terminals()/20))
    # options for displaying label colors.
    if label_colors:
        if callable(label_colors):
            def get_label_color(label):
                return label_colors(label)
        else:
            # label_colors is presumed to be a dict
            def get_label_color(label):
                return label_colors.get(label, 'black')
    else:
        def get_label_color(label):
            # if label_colors is not specified, use black
            return 'black'

    # Layout

    def get_x_positions(tree):
        """Create a mapping of each clade to its horizontal position.

        Dict of {clade: x-coord}
        """
        depths = tree.depths()
        # If there are no branch lengths, assume unit branch lengths
        if not max(depths.values()):
            depths = tree.depths(unit_branch_lengths=True)
        return depths

    def get_y_positions(tree):
        """Create a mapping of each clade to its vertical position.

        Dict of {clade: y-coord}.
        Coordinates are negative, and integers for tips.
        """
        maxheight = tree.count_terminals()
        # Rows are defined by the tips
        heights = dict((tip, maxheight - i)
                       for i, tip in enumerate(reversed(tree.get_terminals())))

        # Internal nodes: place at midpoint of children
        def calc_row(clade):
            for subclade in clade:
                if subclade not in heights:
                    calc_row(subclade)
            # Closure over heights
            heights[clade] = (heights[clade.clades[0]] +
                              heights[clade.clades[-1]]) / 2.0

        if tree.root.clades:
            calc_row(tree.root)
        return heights

    x_posns = get_x_positions(tree)
    y_posns = get_y_positions(tree)


    size = kwargs.get('size',(12,8))
    fig = plt.figure(figsize=size)
    if colorbar:
        import numpy as np
        import matplotlib.gridspec as gridspec
        d_v = size[1]/size[0]
        gs = gridspec.GridSpec(int(10*d_v),1,fig)
        axes = fig.add_subplot(gs[:-1])
        colorbarax=fig.add_subplot(gs[-1])
        gradient = np.linspace(0, 1, 256)
        gradient = np.vstack((gradient, gradient))
        colorbarax.imshow(gradient,aspect='auto', cmap=plt.get_cmap('cool'))
        colorbarax.set_xlim(-85,256+85)
        colorbarax.set_ylim(0,5)
        colorbarax.set_aspect('auto')
        colorbarax.text(-20,0.2,'Low',fontsize=12)
        colorbarax.text(259,0.2,'High',fontsize=12)
        colorbarax.set_axis_off()
    else:
        axes = fig.add_subplot(1, 1, 1,label='tree')

    def draw_clade_lines(use_linecollection=False, orientation='horizontal',
                         y_here=0, x_start=0, x_here=0, y_bot=0, y_top=0,
                         color='black', lw='.02'):
        """Create a line with or without a line collection object.

        Graphical formatting of the lines representing clades in the plot can be
        customized by altering this function.
        """
        if not use_linecollection and orientation == 'horizontal':
            axes.hlines(y_here, x_start, x_here, color=color, lw=lw)
        elif use_linecollection and orientation == 'horizontal':
            horizontal_linecollections.append(mpcollections.LineCollection(
                [[(x_start, y_here), (x_here, y_here)]], color=color, lw=lw),)
        elif not use_linecollection and orientation == 'vertical':
            axes.vlines(x_here, y_bot, y_top, color=color)
        elif use_linecollection and orientation == 'vertical':
            vertical_linecollections.append(mpcollections.LineCollection(
                [[(x_here, y_bot), (x_here, y_top)]], color=color, lw=lw),)

    def draw_clade(clade, x_start, color, lw=0.05):
        """Recursively draw a tree, down from the given clade."""
        x_here = x_posns[clade]
        y_here = y_posns[clade]
        # phyloXML-only graphics annotations
        if hasattr(clade, 'color') and clade.color is not None:
            color = clade.color.to_hex()
        if hasattr(clade, 'width') and clade.width is not None:
            lw = clade.width * plt.rcParams['lines.linewidth']
        # Draw a horizontal line from start to here
        draw_clade_lines(use_linecollection=True, orientation='horizontal',
                         y_here=y_here, x_start=x_start, x_here=x_here, color=color, lw=lw)
        # Add node/taxon labels
        label = label_func(clade)
        if label not in (None, clade.__class__.__name__):
            axes.text(x_here, y_here, ' %s' %
                      label, verticalalignment='center',
                      color=get_label_color(clade.name),fontsize=labelfontsize)


        if clade.clades:
            # Draw a vertical line connecting all children
            y_top = y_posns[clade.clades[0]]
            y_bot = y_posns[clade.clades[-1]]
            # Only apply widths to horizontal lines, like Archaeopteryx
            draw_clade_lines(use_linecollection=True, orientation='vertical',
                             x_here=x_here, y_bot=y_bot, y_top=y_top, color=color, lw=lw)
            # Draw descendents
            for child in clade:
                draw_clade(child, x_here, color, lw)

    draw_clade(tree.root, 0, 'k', 0.3) #plt.rcParams['lines.linewidth']

    # If line collections were used to create clade lines, here they are added
    # to the pyplot plot.
    for i in horizontal_linecollections:
        axes.add_collection(i)
    for i in vertical_linecollections:
        axes.add_collection(i)

    # Aesthetics

    if hasattr(tree, 'name') and tree.name:
        axes.set_title(tree.name)
    axes.set_xlabel('Branch length')
    axes.set_ylabel('Taxa')
    # Add margins around the tree to prevent overlapping the axes
    xmax = max(x_posns.values())
    axes.set_xlim(-0.05 * xmax, 1.25 * xmax)
    # Also invert the y-axis (origin at the top)
    # Add a small vertical margin, but avoid including 0 and N+1 on the y axis
    axes.set_ylim(max(y_posns.values()) + 0.8, 0.2)

    plt.tight_layout()

    if save:
        plt.savefig(save,dpi=300)
    if do_show:
        plt.show()
