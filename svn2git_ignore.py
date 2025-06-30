#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import click
import fnmatch
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


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


def process_directory(path: str, recursive: bool = False, max_depth: int = 0, threads: int = 4) -> List[tuple[str, str]]:
    """
    处理目录，获取所有svn:ignore配置，支持递归深度限制和多线程并行
    """
    results = []
    base_path = os.path.abspath(path)

    if not recursive:
        ignore_config = get_svn_ignore(path)
        if ignore_config:
            rel_path = os.path.relpath(path, base_path)
            rel_path = '.' if rel_path == '.' else rel_path
            results.append((rel_path, ignore_config))
        return results

    # 统计收集目录耗时
    t0 = time.time()
    dirs_to_process = []
    for root, dirs, _ in os.walk(path, topdown=True):
        if '.svn' in dirs:
            dirs.remove('.svn')
        rel_path = os.path.relpath(root, base_path)
        if rel_path == '.':
            depth = 0
        else:
            depth = rel_path.count(os.sep) + 1
        if max_depth > 0 and depth > max_depth:
            dirs.clear()
            continue
        dirs_to_process.append(root)
        ignore_config = get_svn_ignore(root)
        ignore_patterns = [p.strip() for p in (ignore_config or '').splitlines() if p.strip()]
        if ignore_patterns:
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in ignore_patterns)]
    t1 = time.time()
    click.echo(f"共需处理 {len(dirs_to_process)} 个目录，收集目录耗时：{t1-t0:.2f} 秒")

    # 统计递归处理耗时
    t2 = time.time()
    if threads > 10:
        threads = 10

    with ThreadPoolExecutor(max_workers=threads) as executor:
        future_to_path = {executor.submit(get_svn_ignore, d): d for d in dirs_to_process}
        for idx, future in enumerate(as_completed(future_to_path), 1):
            d = future_to_path[future]
            rel_path = os.path.relpath(d, base_path)
            rel_path = '.' if rel_path == '.' else rel_path
            click.echo(f"[{idx}/{len(dirs_to_process)}] 处理: {rel_path}")
            try:
                ignore_config = future.result()
                if ignore_config:
                    results.append((rel_path, ignore_config))
            except Exception as e:
                click.echo(f"警告: 处理 {rel_path} 时出错: {e}", err=True)
    t3 = time.time()
    click.echo(f"递归处理耗时：{t3-t2:.2f} 秒")

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
@click.option('--threads', type=int, default=4, help='并行线程数（最大10，默认4）')
def convert(path: str, recursive: bool, output_file: str, max_depth: int, threads: int):
    """将指定目录的SVN ignore配置转换为.gitignore格式"""
    try:
        subprocess.run(['svn', 'info', path], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        click.echo(f"错误: {path} 不是有效的SVN工作副本", err=True)
        return
    
    click.echo(f"正在处理目录: {path}")
    if recursive:
        click.echo("启用递归处理子目录")
        if max_depth > 0:
            click.echo(f"递归最大深度: {max_depth}")
        if threads > 10:
            threads = 10
        click.echo(f"并行线程数: {threads}")
    
    ignore_configs = process_directory(path, recursive, max_depth, threads)
    
    if not ignore_configs:
        click.echo("未找到任何svn:ignore配置")
        return
    
    gitignore_content = convert_to_gitignore(ignore_configs)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    
    click.echo(f"已成功将svn:ignore配置转换并保存到: {output_file}")


if __name__ == '__main__':
    cli() 