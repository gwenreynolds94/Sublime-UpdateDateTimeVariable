import sublime
import sublime_plugin
import re
from datetime import datetime as right
from time import time
from ctypes import windll

# MsgBox return values
YES = 6
NO = 7

# Formatting constants from settings
DTV = "{@datetime}"
DTVS = "{@datetimestr}"


# ctypes MessageBoxW functions for displaying popups
def MsgBoxOK(msg, cap):
    windll.user32.MessageBoxW(0, msg, cap, 0)


def MsgBoxOKCancel(msg, cap):
    return windll.user32.MessageBoxW(0, msg, cap, 1)


def MsgBoxYesNo(msg, cap):
    return windll.user32.MessageBoxW(0, msg, cap, 4)



def MatchAndReplaceLineSimple(haystack, repl_patt_c, repl_str):
    new_line = ''
    re_grp = haystack.group()
    re_endings = repl_patt_c.split(re_grp)
    repl_match = repl_patt_c.search(re_grp)
    repl_grp = repl_match.group()
    new_line = repl_str.join(re_endings)
    return new_line

def UpdateDateTimeInFile(file_path, line_f, datetime_f, match_mult, is_debug):
    datetime = right.now().strftime(datetime_f)

    # stores non-variable text used in the line_format as a list >> lf_chars
    lf_pat = re.escape(DTV) + r"|" + re.escape(DTVS)
    lf_chars = re.split(lf_pat, line_f)

    # stores datetimes in line_format as a re iterable match object >> lf_iter
    lf_patg = r"(" +  re.escape(DTV) + r")|(" + re.escape(DTVS) + r")"
    lf_c = re.compile(lf_patg)
    lf_iter = lf_c.finditer(line_f)

    # stores datetimes in line_format as strings in list >> iter_groups
    # keeps count of them >> iter_count
    iter_groups = []
    iter_count = 0
    for i in lf_iter:
        grp = i.group()
        iter_groups.append(grp)
        iter_count += 1

    # keeps count of non-variable text in line_format (readbility for my sake)
    char_count = 0
    for c in lf_chars:
        char_count += 1

    # builds re patterns from line_format:
    # ...>>line_match_pattern     for matching the entire line
    # ...>>line_repl_pattern      for matching text described by line_format
    # computes datetime variables, combines them with non-variable text,
    # ...outputs to both a list of individual parts and a joined string
    # ...>>lf_split
    # ...>>ln_str
    lf_ind = 0
    starts_with_char = True if line_f.startswith(lf_chars[0]) else False
    ends_with_char = True if line_f.endswith(lf_chars[char_count-1]) else False
    lf_split = []
    # each loop in for starts by adding datetime
    # ...so it checks if non-datetime text comes first and addresses that
    if starts_with_char:
        ln_str = lf_chars[0]
        lf_split.append(lf_chars[0])
        line_match_pattern = r".*" + re.escape(lf_chars[0])
        line_repl_pattern = re.escape(lf_chars[0])
    else:
        ln_str = ""
        line_match_pattern = r".*"
        line_repl_pattern = r""
    for ind in iter_groups:
        # insert datetime
        if ind.endswith('str}'):
            ln_str += '"' + datetime + '"'
        else:
            ln_str += datetime
        # appends {@datetime} or {@datetimestr}
        lf_split.append(ind)
        # increment loop index
        lf_ind += 1
        # comes after increment to deal with possibly varying lengths of
        # ...the loop's iterable and lf_chars
        if lf_ind < char_count:
            add_to_pattern = r".*" + re.escape(lf_chars[lf_ind])
            line_match_pattern += add_to_pattern
            line_repl_pattern += add_to_pattern
            ln_str += lf_chars[lf_ind]
            lf_split.append(lf_chars[lf_ind])

    # finish up alterations to line_match_pattern
    # ...matching all chars after pattern
    # ...adding support for using either single or double quotes
    line_match_pattern += r".*\s"
    line_pattern_split = re.split("[\\\"|\\\']",line_match_pattern)
    l_mat_with_quotes = r""
    for pat in line_pattern_split:
        if pat.endswith("\\"):
            pat = pat[:-1]
        l_mat_with_quotes += pat
        if pat != line_pattern_split[-1]:
            l_mat_with_quotes += r'[\"' + r"|\']"
    line_match_pattern = l_mat_with_quotes
    # compile patterns
    ln_r_compiled = re.compile(line_match_pattern)
    repl_compiled = re.compile(line_repl_pattern)

    # variables to be modified by the file loop
    new_file = ""
    line_replaced = False
    line_no = 1
    bug_numbers = []
    bug_lines = []

    # The file loop for matching and replacing lines in the target script
    # ...Adds each new line to a variable to overwrite the script with
    file = open(file_path, "r")
    for line in file:
        line_match = ln_r_compiled.search(line)
        if line_replaced and not match_mult or not line_match:
            new_file += line
            line_no += 1
            continue
        else:
            new_line = MatchAndReplaceLineSimple(line_match, repl_compiled, ln_str)
            new_file += new_line
            bug_numbers.append(line_no)
            bug_lines.append(new_line)
            line_no += 1
    file.close()

    # Either commit line changes to the script or display changes in a popup
    # ... depending on the value of "debug" in preferences
    if is_debug:
        out_msg = ""
        bug_index = 0
        for line in bug_lines:
            out_msg += "{}> ".format(bug_numbers[bug_index])
            out_msg += line + "\n"
            bug_index += 1
        MsgBoxOK(out_msg, "UpdateDateTimeVariable DEBUG")
    else:
        file = open(file_path, "w")
        file.write(new_file)
        file.close()


class UpdateDateTimeVariableOnSaveListener(sublime_plugin.EventListener):
    def on_post_save(self, view):
        usr_prefs = "UpdateDateTimeVariable.sublime-settings"
        usr_prefs_dict = sublime.load_settings(usr_prefs)
        if usr_prefs_dict.get("project_to_listen_for"):
            project = usr_prefs_dict.get("project_to_listen_for") + '.sublime-project'
            window = sublime.active_window()
            cur_project = window.project_file_name()
            if isinstance(cur_project, str):
                cur_project = cur_project.rsplit("\\", 1)[1]
                if cur_project == project:
                    f_path = usr_prefs_dict.get("file_path")
                    l_format = usr_prefs_dict.get("line_format")
                    dt_format = usr_prefs_dict.get("datetime_format")
                    m_mult = usr_prefs_dict.get("match_multiple")
                    d_bug = usr_prefs_dict.get("debug")
                    if "%" not in dt_format:
                        dt_format = "'%d-%m-%Y %H:%M:%S'"
                    if not isinstance(m_mult, bool):
                        m_mult = True
                    if ":\\" in f_path or "/" in f_path:
                        if DTV in l_format or DTVS in l_format:
                            UpdateDateTimeInFile(f_path, l_format, dt_format, m_mult, d_bug)



class SetUpdateDateTimeProjectAndFileCommand(sublime_plugin.WindowCommand):
    def run(self):
        usr_prefs = "UpdateDateTimeVariable.sublime-settings"
        usr_prefs_dict = sublime.load_settings(usr_prefs)
        cur_project = self.window.project_file_name()
        cur_file = self.window.active_view().file_name()
        if isinstance(cur_project, str):
            cur_project = cur_project.rsplit("\\", 1)[1]
            cur_project = cur_project.rsplit(".", 1)[0]
            msg = "UpdateDateTimeVariable will start listening to saves on "\
                  "the currently active project:\n" + cur_project + "\n"\
                  "\nIt will update the file:\n" + cur_file + "\n"\
                  "\nWould you like to proceed?"
            cap = "Set project save listener and file to update?"
            proceedQuery = MsgBoxYesNo(msg, cap)
            if proceedQuery == YES:
                usr_prefs_dict.set("project_to_listen_for", cur_project)
                usr_prefs_dict.set("file_path", cur_file)
                sublime.save_settings(usr_prefs)
        else:
            sublime.status_message("   !!!   Could not find project in active window   !!!")
