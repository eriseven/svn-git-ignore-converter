#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import click
import fnmatch
from typing import List, Optional


def get_svn_ignore(path: str) -> Optional[str]:
    """
    获取指定路径的svn:ignore属性值
    
    Args:
        path: 目标路径
        
    Returns:
        str: svn:ignore属性值，如果不存在则返回None
    """
    try:
        result = subprocess.run(
            ['svn', 'propget', 'svn:ignore', path],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip() if result.stdout.strip() else None
    except subprocess.CalledProcessError:
        return None


def process_directory(path: str, recursive: bool = False, max_depth: int = 0) -> List[tuple[str, str]]:
    """
    处理目录，获取所有svn:ignore配置
    支持递归深度限制
    """
    results = []
    base_path = os.path.abspath(path)
    
    if not recursive:
        # 非递归模式保持简单
        ignore_config = get_svn_ignore(path)
        if ignore_config:
            rel_path = os.path.relpath(path, base_path)
            rel_path = '.' if rel_path == '.' else rel_path
            results.append((rel_path, ignore_config))
        return results

    # 使用os.walk进行递归处理，并进行目录剪枝
    for root, dirs, _ in os.walk(path, topdown=True):
        # 跳过.svn目录
        if '.svn' in dirs:
            dirs.remove('.svn')

        # 计算当前递归深度
        rel_path = os.path.relpath(root, base_path)
        if rel_path == '.':
            depth = 0
        else:
            depth = rel_path.count(os.sep) + 1
        if max_depth > 0 and depth > max_depth:
            # 超过最大深度则不再递归其子目录
            dirs.clear()
            continue

        rel_path_display = rel_path
        click.echo(f"正在处理: {rel_path_display}")

        # 获取并处理当前目录的ignore配置
        ignore_config = get_svn_ignore(root)
        if ignore_config:
            rel_path = '.' if rel_path == '.' else rel_path
            results.append((rel_path, ignore_config))

        # 根据当前目录的ignore规则，剪枝子目录
        ignore_patterns = [p.strip() for p in (ignore_config or '').splitlines() if p.strip()]
        if ignore_patterns:
            # 使用列表推导式过滤被忽略的目录
            # dirs[:] 就地修改列表，确保os.walk后续能看到变化
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in ignore_patterns)]

    return results


def convert_to_gitignore(ignore_configs: List[tuple[str, str]]) -> str:
    """
    将SVN ignore配置转换为.gitignore格式，统一路径分隔符为/
    """
    gitignore_content = []
    
    for path, config in ignore_configs:
        # 统一路径分隔符为/
        norm_path = path.replace(os.sep, '/') if path != '.' else '.'
        if norm_path != '.':
            gitignore_content.append(f"\n# {norm_path} 目录的忽略规则")
        
        for pattern in config.splitlines():
            pattern = pattern.strip()
            if not pattern or pattern.startswith('#'):
                continue
                
            if norm_path == '.':
                gitignore_content.append(pattern)
            else:
                # 路径和模式拼接后统一分隔符
                combined = f"{norm_path}/{pattern}".replace('\\', '/').replace('//', '/')
                gitignore_content.append(combined)
    
    return '\n'.join(gitignore_content)


@click.group()
def cli():
    """SVN ignore 配置转换工具"""
    pass


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True, help='递归处理子目录')
@click.option('--output-file', '-o', type=click.Path(), default='.gitignore', help='输出文件路径（默认：.gitignore）')
@click.option('--max-depth', type=int, default=0, help='递归的最大深度（0为不限制）')
def convert(path: str, recursive: bool, output_file: str, max_depth: int):
    """将指定目录的SVN ignore配置转换为.gitignore格式"""
    try:
        # 检查目录是否是SVN工作副本
        subprocess.run(['svn', 'info', path], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        click.echo(f"错误: {path} 不是有效的SVN工作副本", err=True)
        return
    
    click.echo(f"正在处理目录: {path}")
    if recursive:
        click.echo("启用递归处理子目录")
        if max_depth > 0:
            click.echo(f"递归最大深度: {max_depth}")
    
    # 获取所有ignore配置
    ignore_configs = process_directory(path, recursive, max_depth)
    
    if not ignore_configs:
        click.echo("未找到任何svn:ignore配置")
        return
    
    # 转换为.gitignore格式
    gitignore_content = convert_to_gitignore(ignore_configs)
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    
    click.echo(f"已成功将svn:ignore配置转换并保存到: {output_file}")


if __name__ == '__main__':
    cli() 