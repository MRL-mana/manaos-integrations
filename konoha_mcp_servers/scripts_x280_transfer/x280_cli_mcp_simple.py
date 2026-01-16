#!/usr/bin/env python3
"""
X280 CLI MCP Server - Simple Version
"""

import subprocess

class X280CLIMCP:
    def __init__(self):
        self.cli_tools = {
            'github': 'gh',
            'gcloud': 'gcloud', 
            'aws': 'aws',
            'azure': 'az',
            'openai': 'openai',
            'docker': 'docker'
        }
    
    def execute_command(self, tool, args):
        """Execute CLI command"""
        try:
            if tool not in self.cli_tools:
                return {"success": False, "error": f"Unknown tool: {tool}"}
            
            cmd = [self.cli_tools[tool]] + args
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def github_repos(self):
        """Get GitHub repositories"""
        return self.execute_command('github', ['repo', 'list', '--json', 'name,description'])
    
    def gcloud_projects(self):
        """Get GCP projects"""
        return self.execute_command('gcloud', ['projects', 'list', '--format=json'])
    
    def aws_instances(self):
        """Get AWS instances"""
        return self.execute_command('aws', ['ec2', 'describe-instances', '--output', 'json'])
    
    def docker_containers(self):
        """Get Docker containers"""
        return self.execute_command('docker', ['ps', '-a', '--format', 'json'])

if __name__ == "__main__":
    server = X280CLIMCP()
    print("X280 CLI MCP Server ready")
