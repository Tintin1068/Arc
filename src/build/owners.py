# ARC MOD TRACK "third_party/tools/depot_tools/owners.py"
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A database of OWNERS files.

OWNERS files indicate who is allowed to approve changes in a specific directory
(or who is allowed to make changes without needing approval of another OWNER).
Note that all changes must still be reviewed by someone familiar with the code,
so you may need approval from both an OWNER and a reviewer in many cases.

The syntax of the OWNERS file is, roughly:

lines     := (\s* line? \s* "\n")*

line      := directive
          | "per-file" \s+ glob \s* "=" \s* directive
          | comment

directive := "set noparent"
          |  "file:" glob
          |  email_address
          |  "*"

glob      := [a-zA-Z0-9_-*?]+

comment   := "#" [^"\n"]*

Email addresses must follow the foo@bar.com short form (exact syntax given
in BASIC_EMAIL_REGEXP, below). Filename globs follow the simple unix
shell conventions, and relative and absolute paths are not allowed (i.e.,
globs only refer to the files in the current directory).

If a user's email is one of the email_addresses in the file, the user is
considered an "OWNER" for all files in the directory.

If the "per-file" directive is used, the line only applies to files in that
directory that match the filename glob specified.

If the "set noparent" directive used, then only entries in this OWNERS file
apply to files in this directory; if the "set noparent" directive is not
used, then entries in OWNERS files in enclosing (upper) directories also
apply (up until a "set noparent is encountered").

If "per-file glob=set noparent" is used, then global directives are ignored
for the glob, and only the "per-file" owners are used for files matching that
glob.

If the "file:" directive is used, the referred to OWNERS file will be parsed and
considered when determining the valid set of OWNERS. If the filename starts with
"//" it is relative to the root of the repository, otherwise it is relative to
the current file

Examples for all of these combinations can be found in tests/owners_unittest.py.
"""

import collections
import fnmatch
import random
import re


# If this is present by itself on a line, this means that everyone can review.
EVERYONE = '*'


# Recognizes 'X@Y' email addresses. Very simplistic.
BASIC_EMAIL_REGEXP = r'^[\w\-\+\%\.]+\@[\w\-\+\%\.]+$'


def _assert_is_collection(obj):
  assert not isinstance(obj, basestring)
  # Module 'collections' has no 'Iterable' member
  # pylint: disable=E1101
  if hasattr(collections, 'Iterable') and hasattr(collections, 'Sized'):
    assert (isinstance(obj, collections.Iterable) and
            isinstance(obj, collections.Sized))


class SyntaxErrorInOwnersFile(Exception):
  def __init__(self, path, lineno, msg):
    super(SyntaxErrorInOwnersFile, self).__init__((path, lineno, msg))
    self.path = path
    self.lineno = lineno
    self.msg = msg

  def __str__(self):
    return '%s:%d syntax error: %s' % (self.path, self.lineno, self.msg)


# ARC MOD BEGIN
# Add a ReviewerSet as a more detailed result for querying for reviewers.
class ReviewerAssignment():
  """Class that indicates what a given reviewer should review."""
  def __init__(self):
    # Map from comments to lists of files for that comment
    self.comments = collections.defaultdict(list)
    # Other reviewers who also could have been chosen
    self.alternates = set()
    # Set of directories under review (any comment)
    self.dirs = set()

class ReviewerSet():
  """Class that holds the set of reviewers and what they should review."""
  def __init__(self):
    self.reviewers = collections.defaultdict(ReviewerAssignment)

  def add(self, primary, directory, files, comment):
    self.reviewers[primary].comments[comment].extend(files)
    self.reviewers[primary].dirs |= set([directory])

  def add_alternates(self, primary, alternates):
    self.reviewers[primary].alternates |= set(alternates)

  def get_reviewers(self):
    return self.reviewers.keys()

  def get_review_dirs(self, primary):
    return self.reviewers[primary].dirs

  def is_empty(self):
    if self._reviewers:
      return False
    else:
      return True

  def reduce_everyone(self):
    """Simplify the list if EVERYONE is in it."""
    if EVERYONE in self.reviewers:
      if len(self.reviewers) == 1:
        self.reviewers['<anyone>'] = self.reviewers[EVERYONE]
      del self.reviewers[EVERYONE]


# ARC MOD END
class Database(object):
  """A database of OWNERS files for a repository.

  This class allows you to find a suggested set of reviewers for a list
  of changed files, and see if a list of changed files is covered by a
  list of reviewers."""

  def __init__(self, root, fopen, os_path):
    """Args:
      root: the path to the root of the Repository
      open: function callback to open a text file for reading
      os_path: module/object callback with fields for 'abspath', 'dirname',
          'exists', 'join', and 'relpath'
    """
    self.root = root
    self.fopen = fopen
    self.os_path = os_path

    # Pick a default email regexp to use; callers can override as desired.
    self.email_regexp = re.compile(BASIC_EMAIL_REGEXP)

    # Mapping of owners to the paths or globs they own.
    self._owners_to_paths = {EVERYONE: set()}

    # Mapping of paths to authorized owners.
    self._paths_to_owners = {}

    # Mapping reviewers to the preceding comment per file in the OWNERS files.
    self.comments = {}

    # Set of paths that stop us from looking above them for owners.
    # (This is implicitly true for the root directory).
    self._stop_looking = set([''])

    # Set of files which have already been read.
    self.read_files = set()

  # ARC MOD BEGIN
  # Introduce reviewer_set_for.
  def reviewers_for(self, files, author):
    return set(self.reviewer_set_for(files,author).get_reviewers())

  def reviewer_set_for(self, files, author):
    """Returns a suggested set of reviewers that will cover the files.

    files is a sequence of paths relative to (and under) self.root.
    If author is nonempty, we ensure it is not included in the set returned
    in order avoid suggesting the author as a reviewer for their own changes."""
    self._check_paths(files)
    self.load_data_needed_for(files)
    suggested_owners = self._covering_set_of_owners_for(files, author)
    # We reduce EVERYONE in ReviewerSet instead of doing it here.
    suggested_owners.reduce_everyone()
    return suggested_owners
  # ARC MOD END

  def files_not_covered_by(self, files, reviewers):
    """Returns the files not owned by one of the reviewers.

    Args:
        files is a sequence of paths relative to (and under) self.root.
        reviewers is a sequence of strings matching self.email_regexp.
    """
    self._check_paths(files)
    self._check_reviewers(reviewers)
    self.load_data_needed_for(files)

    return set(f for f in files if not self._is_obj_covered_by(f, reviewers))

  def _check_paths(self, files):
    def _is_under(f, pfx):
      return self.os_path.abspath(self.os_path.join(pfx, f)).startswith(pfx)
    _assert_is_collection(files)
    assert all(not self.os_path.isabs(f) and
                _is_under(f, self.os_path.abspath(self.root)) for f in files)

  def _check_reviewers(self, reviewers):
    _assert_is_collection(reviewers)
    assert all(self.email_regexp.match(r) for r in reviewers)

  def _is_obj_covered_by(self, objname, reviewers):
    reviewers = list(reviewers) + [EVERYONE]
    while True:
      for reviewer in reviewers:
        for owned_pattern in self._owners_to_paths.get(reviewer, set()):
          if fnmatch.fnmatch(objname, owned_pattern):
            return True
      if self._should_stop_looking(objname):
        break
      objname = self.os_path.dirname(objname)
    return False

  def _enclosing_dir_with_owners(self, objname):
    """Returns the innermost enclosing directory that has an OWNERS file."""
    dirpath = objname
    while not self._owners_for(dirpath):
      if self._should_stop_looking(dirpath):
        break
      dirpath = self.os_path.dirname(dirpath)
    return dirpath

  def load_data_needed_for(self, files):
    for f in files:
      dirpath = self.os_path.dirname(f)
      while not self._owners_for(dirpath):
        self._read_owners(self.os_path.join(dirpath, 'OWNERS'))
        if self._should_stop_looking(dirpath):
          break
        dirpath = self.os_path.dirname(dirpath)

  def _should_stop_looking(self, objname):
    return any(fnmatch.fnmatch(objname, stop_looking)
               for stop_looking in self._stop_looking)

  def _owners_for(self, objname):
    obj_owners = set()
    for owned_path, path_owners in self._paths_to_owners.iteritems():
      if fnmatch.fnmatch(objname, owned_path):
        obj_owners |= path_owners
    return obj_owners

  def _read_owners(self, path):
    owners_path = self.os_path.join(self.root, path)
    if not self.os_path.exists(owners_path):
      return

    if owners_path in self.read_files:
      return

    self.read_files.add(owners_path)

    comment = []
    dirpath = self.os_path.dirname(path)
    in_comment = False
    lineno = 0
    for line in self.fopen(owners_path):
      lineno += 1
      line = line.strip()
      if line.startswith('#'):
        if not in_comment:
          comment = []
        comment.append(line[1:].strip())
        in_comment = True
        continue
      if line == '':
        continue
      in_comment = False

      if line == 'set noparent':
        self._stop_looking.add(dirpath)
        continue

      m = re.match('per-file (.+)=(.+)', line)
      if m:
        glob_string = m.group(1).strip()
        directive = m.group(2).strip()
        full_glob_string = self.os_path.join(self.root, dirpath, glob_string)
        if '/' in glob_string or '\\' in glob_string:
          raise SyntaxErrorInOwnersFile(owners_path, lineno,
              'per-file globs cannot span directories or use escapes: "%s"' %
              line)
        relative_glob_string = self.os_path.relpath(full_glob_string, self.root)
        self._add_entry(relative_glob_string, directive, 'per-file line',
                        owners_path, lineno, '\n'.join(comment))
        continue

      if line.startswith('set '):
        raise SyntaxErrorInOwnersFile(owners_path, lineno,
            'unknown option: "%s"' % line[4:].strip())

      self._add_entry(dirpath, line, 'line', owners_path, lineno,
                      ' '.join(comment))

  def _add_entry(self, path, directive,
                 line_type, owners_path, lineno, comment):
    if directive == 'set noparent':
      self._stop_looking.add(path)
    elif directive.startswith('file:'):
      owners_file = self._resolve_include(directive[5:], owners_path)
      if not owners_file:
        raise SyntaxErrorInOwnersFile(owners_path, lineno,
            ('%s does not refer to an existing file.' % directive[5:]))

      self._read_owners(owners_file)

      dirpath = self.os_path.dirname(owners_file)
      for key in self._owners_to_paths:
        if not dirpath in self._owners_to_paths[key]:
          continue
        self._owners_to_paths[key].add(path)

      if dirpath in self._paths_to_owners:
        self._paths_to_owners.setdefault(path, set()).update(
            self._paths_to_owners[dirpath])

    elif self.email_regexp.match(directive) or directive == EVERYONE:
      self.comments.setdefault(directive, {})
      self.comments[directive][path] = comment
      self._owners_to_paths.setdefault(directive, set()).add(path)
      self._paths_to_owners.setdefault(path, set()).add(directive)
    else:
      raise SyntaxErrorInOwnersFile(owners_path, lineno,
          ('%s is not a "set" directive, file include, "*", '
           'or an email address: "%s"' % (line_type, directive)))

  def _resolve_include(self, path, start):
    if path.startswith('//'):
      include_path = path[2:]
    else:
      assert start.startswith(self.root)
      start = self.os_path.dirname(self.os_path.relpath(start, self.root))
      include_path = self.os_path.join(start, path)

    owners_path = self.os_path.join(self.root, include_path)
    if not self.os_path.exists(owners_path):
      return None

    return include_path

  # ARC MOD BEGIN
  # Support ReviewerSet
  def _get_most_specific_comment(self, owner, dir):
    most_specific_comment = ''
    search_dir = dir
    while True:
      if search_dir in self.comments[owner]:
        most_specific_comment = self.comments[owner][search_dir]
        break
      if not search_dir: break
      search_dir = self.os_path.dirname(search_dir)
    return most_specific_comment

  # ARC MOD END
  def _covering_set_of_owners_for(self, files, author):
    # ARC MOD BEGIN
    # Return a ReviewerSet instead of just a list of reviewer emails.
    dirs_to_files_map = collections.defaultdict(list)
    for f in files:
      dirs_to_files_map[self._enclosing_dir_with_owners(f)].append(f)
    dirs_remaining = set(dirs_to_files_map.keys())
    all_possible_owners = self.all_possible_owners(dirs_remaining, author)
    suggested_owners = ReviewerSet()
    while dirs_remaining:
      primary, alternates = self.lowest_cost_owner_with_alternates(
          all_possible_owners,
          dirs_remaining)
      dirs_to_remove = set(el[0] for el in all_possible_owners[primary])
      for d in dirs_to_remove:
        comment = self._get_most_specific_comment(primary, d)
        suggested_owners.add(primary, d, dirs_to_files_map[d], comment)
      # Add alternates.  Every alternate needs to own every directory that
      # is currently assigned to the primary reviewer.
      review_dirs = suggested_owners.get_review_dirs(primary)
      final_alternates = []
      for alternate in alternates:
        if review_dirs.issubset(
            set(el[0] for el in all_possible_owners[alternate])):
          final_alternates.append(alternate)
      suggested_owners.add_alternates(primary, final_alternates)
      dirs_remaining -= dirs_to_remove
    # ARC MOD END
    return suggested_owners

  def all_possible_owners(self, dirs, author):
    """Returns a list of (potential owner, distance-from-dir) tuples; a
    distance of 1 is the lowest/closest possible distance (which makes the
    subsequent math easier)."""
    all_possible_owners = {}
    for current_dir in dirs:
      dirname = current_dir
      distance = 1
      while True:
        for owner in self._owners_for(dirname):
          if author and owner == author:
            continue
          all_possible_owners.setdefault(owner, [])
          # If the same person is in multiple OWNERS files above a given
          # directory, only count the closest one.
          if not any(current_dir == el[0] for el in all_possible_owners[owner]):
            all_possible_owners[owner].append((current_dir, distance))
        if self._should_stop_looking(dirname):
          break
        dirname = self.os_path.dirname(dirname)
        distance += 1
    return all_possible_owners

  @staticmethod
  def total_costs_by_owner(all_possible_owners, dirs):
    # We want to minimize both the number of reviewers and the distance
    # from the files/dirs needing reviews. The "pow(X, 1.75)" below is
    # an arbitrarily-selected scaling factor that seems to work well - it
    # will select one reviewer in the parent directory over three reviewers
    # in subdirs, but not one reviewer over just two.
    result = {}
    for owner in all_possible_owners:
      total_distance = 0
      num_directories_owned = 0
      for dirname, distance in all_possible_owners[owner]:
        if dirname in dirs:
          total_distance += distance
          num_directories_owned += 1
      if num_directories_owned:
        result[owner] = (total_distance /
                         pow(num_directories_owned, 1.75))
    return result

  # ARC MOD BEGIN
  # Support ReviewerSet
  @staticmethod
  def lowest_cost_owner_with_alternates(all_possible_owners, dirs):
    # ARC MOD END
    total_costs_by_owner = Database.total_costs_by_owner(all_possible_owners,
                                                         dirs)
    # Return the lowest cost owner. In the case of a tie, pick one randomly.
    # ARC MOD BEGIN
    assert total_costs_by_owner, 'No more owners for dirs %s' % dirs
    # ARC MOD END
    lowest_cost = min(total_costs_by_owner.itervalues())
    lowest_cost_owners = filter(
        lambda owner: total_costs_by_owner[owner] == lowest_cost,
        total_costs_by_owner)
    # ARC MOD BEGIN
    # Return the winner and alternates.
    primary = random.Random().choice(lowest_cost_owners)
    return (primary, set(lowest_cost_owners) - set([primary]))

  @staticmethod
  def lowest_cost_owner(all_possible_owners, dirs):
    return Database.lowest_cost_owner_with_alternates(all_possible_owners,
                                                      dirs)[0]
    # ARC MOD END
