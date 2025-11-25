from rdflib import Graph
import pyshacl
from typing import Iterable, Tuple

def get_prefixes(g: Graph):
    return "\n".join(f"PREFIX {prefix}: <{namespace}>" for prefix, namespace in g.namespace_manager.namespaces())

def convert_to_prefixed(uri, g: Graph):
    try:
        prefix, uri_ref, local_name = g.compute_qname(uri)
        return f"{prefix}:{local_name}"
    except Exception as e:
        print(e)
        return uri

def query_to_df(query, g: Graph):
    results = g.query(query)
    formatted_results = [
        [convert_to_prefixed(value, g) if isinstance(value, (str, bytes)) and value.startswith("http") else str(value) for value in row]
        for row in results
    ]
    # NOTE: getting rid of pandas as dependency
    # df = pd.DataFrame(formatted_results, columns=[str(var) for var in results.vars])
    # return df
    columns=[str(var) for var in results.vars]
    return formatted_results, columns

import os

def parse_ttl_files_in_directory(directory_path, g):
    # Iterate through all files in the directory
    for file_name in os.listdir(directory_path):
        # Process only .ttl files
        if file_name.endswith(".ttl"):
            file_path = os.path.join(directory_path, file_name)
            print(f"Processing file: {file_name}")
            # Parse the .ttl file
            try:
                g.parse(file_path, format="turtle")
                # print(f"Parsed {len(g)} triples from {file_name}")
                
            except Exception as e:
                print(f"Error parsing {file_name}: {e}")


def common_pattern(strings: Iterable[str],
                   placeholder: str = "x") -> Tuple[str, str, str]:
    """
    Return a pattern that highlights the part common to *all* strings and
    replaces the differing part with *placeholder*.

    The result is a tuple (prefix, placeholder, suffix).  If you want a
    single string you can join them:  prefix + placeholder + suffix.

    Parameters
    ----------
    strings : iterable of str
        The strings to analyse.
    placeholder : str, default='x'
        Symbol that will stand in for the variable region.

    Returns
    -------
    tuple(str, str, str)
        (common_prefix, placeholder, common_suffix)
    """
    strs = list(strings)
    if not strs:
        return "", placeholder, ""

    # ---------- longest common prefix ----------
    # zip stops at the shortest string, so we can compare column‑wise
    prefix_chars = []
    for chars in zip(*strs):
        if all(c == chars[0] for c in chars):
            prefix_chars.append(chars[0])
        else:
            break
    prefix = "".join(prefix_chars)

    # ---------- longest common suffix ----------
    # reverse strings, do the same thing, then reverse the result
    rev_strs = [s[::-1] for s in strs]
    suffix_chars = []
    for chars in zip(*rev_strs):
        if all(c == chars[0] for c in chars):
            suffix_chars.append(chars[0])
        else:
            break
    suffix = "".join(suffix_chars)[::-1]

    # If the prefix and suffix overlap (possible when the whole string is equal)
    # trim the suffix to avoid duplication.
    if prefix and suffix and len(prefix) + len(suffix) > len(strs[0]):
        suffix = suffix[len(prefix) + len(suffix) - len(strs[0]):]

    # TODO: determine if placeholder is helpful in any way
    # return f"{prefix}{placeholder}{suffix}"
    return f"{prefix}{suffix}"