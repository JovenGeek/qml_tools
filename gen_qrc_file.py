import sys
import argparse
from pprint import pprint
from pathlib import Path

from lxml import etree


def parse_pathdata(pathdata: str):
    # DIRPATH or FILEPATH
    # [prefix:PREFIX;][lang:LANG;]path:DIRPATH or FILEPATH
    # [prefix:PREFIX;][alias:ALIAS;][lang:LANG;]path:FILEPATH
    pathdata = pathdata.strip()
    ret = {}
    if 'path' not in pathdata:
        if ':' in pathdata or ';' in pathdata:
            raise Exception('path error')

        path = Path(pathdata.lower())

        if not path.exists():
            raise Exception('path error')
    else:
        data_dict = dict([
            item.strip().split(':')
            for item in pathdata.split(';')
            if item.strip()
        ])

        if 'path' not in data_dict:
            raise Exception('path error')

        path = Path(data_dict['path'].strip().lower())

        if not path.exists():
            raise Exception('path error')

        if path.is_dir() and 'alias' in data_dict:
            raise Exception('dir error')

        ret.update({
            key: data_dict[key]
            for key in ['prefix', 'alias', 'lang']
            if key in data_dict
        })
    ret['path'] = path
    return ret


def parse_file(file_path):
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise Exception('file 不存在 或 不是文件！')

    ret = []

    path_set = set()
    with open(str(path), 'r') as f:
        path_set = set(
            pathdata.strip()
            for pathdata in f
            if pathdata.strip()
        )
    for pathdata in path_set:
        pathdata = pathdata.strip()
        if pathdata:
            ret.append(parse_pathdata(pathdata))
    return list(ret)


def gen_qrc_file(qrc_dict, outputfile):
    RCC = etree.Element("RCC")
    RCC.set('version', qrc_dict['version'])
    for qresource_dict in qrc_dict["qresources"]:
        qresource_element = etree.SubElement(RCC, "qresource" )
        for attr in ['prefix', 'lang']:
            if attr in qresource_dict:
                qresource_element.set(attr, qresource_dict[attr])

        for file_dict in qresource_dict['files']:
            file_element = etree.SubElement(qresource_element, "file" )
            if 'alias' in file_dict:
                file_element.set('alias', file_dict['alias'])
            file_element.text = file_dict['file']

    tree = etree.ElementTree(RCC)
    tree.write(
        str(outputfile),
        doctype='<!DOCTYPE RCC>',
        pretty_print=True,
        encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(prog='qrc 文件生成脚本', description="根据提供的路径生成 qrc 文件")
    parser.add_argument(
        'pathdata', nargs='*', type=parse_pathdata,
        help='pathdata 路径中不可以包含";"和":"号')
    parser.add_argument(
        '-f', '--file', nargs='?',
        type=str,
        help='pathdata 以文件的方式传递'
    )
    parser.add_argument(
        '-v', '--version', nargs='?',
        default='1.0', type=str,
        help='pathdata 以文件的方式传递'
    )
    parser.add_argument(
        '-o', '--outputfile', nargs='?',
        default='./qml.qrc', type=Path,
        help='输出文件路径（默认为：%(default)s）')
    kargs: dict = vars(parser.parse_args())
    # print(kargs)

    version = kargs['version']
    outputfile = kargs['outputfile']
    txt_path = kargs['file']
    pathdata = kargs['pathdata']

    qresource_list = []
    qrc_dict = {
        'version': version,
        'qresources': qresource_list
    }

    path_list = []
    if txt_path is not None:
        path_list.extend(parse_file(txt_path))
    if pathdata:
        path_list.extend(pathdata)

    qresource_dict = {}
    # [prefix:PREFIX;][alias:ALIAS;][lang:LANG;]path:FILEPATH
    for path_dict in path_list:
        prefix = path_dict.get('prefix')
        prefix_dict = qresource_dict.setdefault(prefix, {})
        lang = path_dict.get('lang')
        file_list = prefix_dict.setdefault(lang, [])
        alias = path_dict.get('alias')
        path: Path = path_dict.get('path')

        if path.is_file():
            file_data = {'file': path.as_posix()}
            if alias is not None:
                file_data['alias'] = alias
            file_list.append(file_data)
        else:
            for path_ in path.rglob('*'):
                if path_.is_file():
                    file_list.append({
                        'file': path_.as_posix()
                    })

    for prefix in qresource_dict:
        for lang in qresource_dict[prefix]:
            qresource_dict[prefix][lang] = sorted(
                qresource_dict[prefix][lang], key=lambda x: x['file'])

    if None in qresource_dict:
        non_prefix_dict = qresource_dict.pop(None)

        if None in non_prefix_dict:
            non_lang = non_prefix_dict.pop(None)
            qresource_list.append({
                'files': non_lang
            })

        for lang in sorted(non_prefix_dict):
            qresource_list.append({
                'lang': lang,
                'files': non_prefix_dict[lang]
            })

    for prefix in sorted(qresource_dict):
        prefix_dict = qresource_dict[prefix]

        if None in prefix_dict:
            non_lang = prefix_dict.pop(None)
            qresource_list.append({
                'prefix': prefix,
                'files': non_lang
            })
        for lang in sorted(prefix_dict):
            qresource_list.append({
                'prefix': prefix,
                'lang': lang,
                'files': prefix_dict[lang]
            })

    gen_qrc_file(qrc_dict, outputfile)


if __name__ == "__main__":
    main()
