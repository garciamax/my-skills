#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const TOKEN = process.env.JOPLIN_TOKEN;
const PORT = process.env.JOPLIN_PORT || '41184';
const BASE_URL = `http://localhost:${PORT}`;

if (!TOKEN && process.argv[2] !== 'ping') {
  console.error('Error: JOPLIN_TOKEN environment variable is required');
  console.error('Get your token from Joplin: Tools → Options → Web Clipper');
  process.exit(1);
}

// HTTP request helper
function request(method, endpoint, data = null, isFormData = false) {
  return new Promise((resolve, reject) => {
    const url = new URL(endpoint, BASE_URL);
    url.searchParams.set('token', TOKEN);

    const options = {
      method,
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      headers: {}
    };

    if (data && !isFormData) {
      options.headers['Content-Type'] = 'application/json';
    }

    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        if (res.statusCode >= 400) {
          try {
            const err = JSON.parse(body);
            reject(new Error(err.error || `HTTP ${res.statusCode}`));
          } catch {
            reject(new Error(`HTTP ${res.statusCode}: ${body}`));
          }
          return;
        }
        try {
          resolve(body ? JSON.parse(body) : {});
        } catch {
          resolve(body);
        }
      });
    });

    req.on('error', reject);

    if (data && !isFormData) {
      req.write(JSON.stringify(data));
    } else if (isFormData) {
      req.write(data);
    }
    req.end();
  });
}

// Multipart form data helper for file uploads
function uploadFile(endpoint, filePath, props = {}) {
  return new Promise((resolve, reject) => {
    const boundary = '----JoplinBoundary' + Date.now();
    const fileName = path.basename(filePath);
    const fileContent = fs.readFileSync(filePath);
    const mimeType = getMimeType(filePath);

    let body = '';
    // Props field
    body += `--${boundary}\r\n`;
    body += `Content-Disposition: form-data; name="props"\r\n\r\n`;
    body += JSON.stringify(props) + '\r\n';
    
    // File field
    body += `--${boundary}\r\n`;
    body += `Content-Disposition: form-data; name="data"; filename="${fileName}"\r\n`;
    body += `Content-Type: ${mimeType}\r\n\r\n`;

    const bodyStart = Buffer.from(body, 'utf8');
    const bodyEnd = Buffer.from(`\r\n--${boundary}--\r\n`, 'utf8');
    const fullBody = Buffer.concat([bodyStart, fileContent, bodyEnd]);

    const url = new URL(endpoint, BASE_URL);
    url.searchParams.set('token', TOKEN);

    const options = {
      method: 'POST',
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      headers: {
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': fullBody.length
      }
    };

    const req = http.request(options, (res) => {
      let responseBody = '';
      res.on('data', chunk => responseBody += chunk);
      res.on('end', () => {
        if (res.statusCode >= 400) {
          try {
            const err = JSON.parse(responseBody);
            reject(new Error(err.error || `HTTP ${res.statusCode}`));
          } catch {
            reject(new Error(`HTTP ${res.statusCode}: ${responseBody}`));
          }
          return;
        }
        try {
          resolve(JSON.parse(responseBody));
        } catch {
          resolve(responseBody);
        }
      });
    });

    req.on('error', reject);
    req.write(fullBody);
    req.end();
  });
}

function getMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mimeTypes = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.png': 'image/png', '.gif': 'image/gif',
    '.pdf': 'application/pdf', '.txt': 'text/plain',
    '.md': 'text/markdown', '.html': 'text/html',
    '.json': 'application/json', '.xml': 'application/xml',
    '.zip': 'application/zip', '.mp3': 'audio/mpeg',
    '.mp4': 'video/mp4', '.webp': 'image/webp',
  };
  return mimeTypes[ext] || 'application/octet-stream';
}

// Download file helper
function downloadFile(endpoint, outputPath) {
  return new Promise((resolve, reject) => {
    const url = new URL(endpoint, BASE_URL);
    url.searchParams.set('token', TOKEN);

    http.get(url.href, (res) => {
      if (res.statusCode >= 400) {
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => reject(new Error(`HTTP ${res.statusCode}: ${body}`)));
        return;
      }
      const file = fs.createWriteStream(outputPath);
      res.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve({ success: true, path: outputPath });
      });
    }).on('error', reject);
  });
}

// Parse command line arguments
function parseArgs(args) {
  const result = { _: [] };
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('--')) {
      const key = args[i].slice(2);
      const next = args[i + 1];
      if (next && !next.startsWith('--')) {
        result[key] = next;
        i++;
      } else {
        result[key] = true;
      }
    } else {
      result._.push(args[i]);
    }
  }
  return result;
}

// Build query string for common options
function buildQuery(args) {
  const params = new URLSearchParams();
  if (args.limit) params.set('limit', args.limit);
  if (args.page) params.set('page', args.page);
  if (args.fields) params.set('fields', args.fields);
  if (args['order-by']) params.set('order_by', args['order-by']);
  if (args['order-dir']) params.set('order_dir', args['order-dir']);
  if (args.type) params.set('type', args.type);
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

// Commands
const commands = {
  ping: async () => {
    try {
      const url = `http://localhost:${PORT}/ping`;
      return new Promise((resolve) => {
        http.get(url, (res) => {
          let body = '';
          res.on('data', chunk => body += chunk);
          res.on('end', () => {
            if (body === 'JoplinClipperServer') {
              resolve({ status: 'ok', message: 'Joplin service is running', port: PORT });
            } else {
              resolve({ status: 'error', message: 'Unexpected response', response: body });
            }
          });
        }).on('error', () => {
          resolve({ status: 'error', message: 'Joplin service is not running', port: PORT });
        });
      });
    } catch (e) {
      return { status: 'error', message: e.message };
    }
  },

  notes: {
    list: async (args) => request('GET', `/notes${buildQuery(args)}`),
    get: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Note ID required');
      return request('GET', `/notes/${id}${buildQuery(args)}`);
    },
    create: async (args) => {
      const data = {};
      if (args.title) data.title = args.title;
      if (args.body) data.body = args.body;
      if (args['body-html']) data.body_html = args['body-html'];
      if (args['parent-id']) data.parent_id = args['parent-id'];
      if (args['is-todo']) data.is_todo = parseInt(args['is-todo']);
      if (args['source-url']) data.source_url = args['source-url'];
      if (!data.title) throw new Error('--title is required');
      return request('POST', '/notes', data);
    },
    update: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Note ID required');
      const data = {};
      if (args.title) data.title = args.title;
      if (args.body) data.body = args.body;
      if (args['parent-id']) data.parent_id = args['parent-id'];
      if (args['is-todo']) data.is_todo = parseInt(args['is-todo']);
      return request('PUT', `/notes/${id}`, data);
    },
    delete: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Note ID required');
      const query = args.permanent ? '?permanent=1' : '';
      return request('DELETE', `/notes/${id}${query}`);
    },
    tags: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Note ID required');
      return request('GET', `/notes/${id}/tags${buildQuery(args)}`);
    },
    resources: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Note ID required');
      return request('GET', `/notes/${id}/resources${buildQuery(args)}`);
    }
  },

  folders: {
    list: async (args) => request('GET', `/folders${buildQuery(args)}`),
    get: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Folder ID required');
      return request('GET', `/folders/${id}${buildQuery(args)}`);
    },
    create: async (args) => {
      const data = {};
      if (args.title) data.title = args.title;
      if (args['parent-id']) data.parent_id = args['parent-id'];
      if (!data.title) throw new Error('--title is required');
      return request('POST', '/folders', data);
    },
    update: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Folder ID required');
      const data = {};
      if (args.title) data.title = args.title;
      if (args['parent-id']) data.parent_id = args['parent-id'];
      return request('PUT', `/folders/${id}`, data);
    },
    delete: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Folder ID required');
      const query = args.permanent ? '?permanent=1' : '';
      return request('DELETE', `/folders/${id}${query}`);
    },
    notes: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Folder ID required');
      return request('GET', `/folders/${id}/notes${buildQuery(args)}`);
    }
  },

  tags: {
    list: async (args) => request('GET', `/tags${buildQuery(args)}`),
    get: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Tag ID required');
      return request('GET', `/tags/${id}${buildQuery(args)}`);
    },
    create: async (args) => {
      const data = {};
      if (args.title) data.title = args.title;
      if (!data.title) throw new Error('--title is required');
      return request('POST', '/tags', data);
    },
    update: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Tag ID required');
      const data = {};
      if (args.title) data.title = args.title;
      return request('PUT', `/tags/${id}`, data);
    },
    delete: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Tag ID required');
      return request('DELETE', `/tags/${id}`);
    },
    notes: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Tag ID required');
      return request('GET', `/tags/${id}/notes${buildQuery(args)}`);
    },
    'add-note': async (args) => {
      const tagId = args._[0];
      const noteId = args._[1];
      if (!tagId || !noteId) throw new Error('Tag ID and Note ID required');
      return request('POST', `/tags/${tagId}/notes`, { id: noteId });
    },
    'remove-note': async (args) => {
      const tagId = args._[0];
      const noteId = args._[1];
      if (!tagId || !noteId) throw new Error('Tag ID and Note ID required');
      return request('DELETE', `/tags/${tagId}/notes/${noteId}`);
    }
  },

  resources: {
    list: async (args) => request('GET', `/resources${buildQuery(args)}`),
    get: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Resource ID required');
      return request('GET', `/resources/${id}${buildQuery(args)}`);
    },
    download: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Resource ID required');
      const output = args.output || args._[1];
      if (!output) throw new Error('--output path required');
      return downloadFile(`/resources/${id}/file`, output);
    },
    upload: async (args) => {
      const filePath = args._[0];
      if (!filePath) throw new Error('File path required');
      if (!fs.existsSync(filePath)) throw new Error(`File not found: ${filePath}`);
      const props = {};
      if (args.title) props.title = args.title;
      return uploadFile('/resources', filePath, props);
    },
    delete: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Resource ID required');
      return request('DELETE', `/resources/${id}`);
    },
    notes: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Resource ID required');
      return request('GET', `/resources/${id}/notes${buildQuery(args)}`);
    }
  },

  search: async (args) => {
    const query = args._[0];
    if (!query) throw new Error('Search query required');
    const params = new URLSearchParams({ query });
    if (args.limit) params.set('limit', args.limit);
    if (args.page) params.set('page', args.page);
    if (args.fields) params.set('fields', args.fields);
    if (args.type) params.set('type', args.type);
    return request('GET', `/search?${params.toString()}`);
  },

  events: {
    list: async (args) => {
      const params = new URLSearchParams();
      if (args.cursor) params.set('cursor', args.cursor);
      if (args.limit) params.set('limit', args.limit);
      const qs = params.toString();
      return request('GET', `/events${qs ? '?' + qs : ''}`);
    },
    get: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Event ID required');
      return request('GET', `/events/${id}`);
    }
  },

  revisions: {
    list: async (args) => request('GET', `/revisions${buildQuery(args)}`),
    get: async (args) => {
      const id = args._[0];
      if (!id) throw new Error('Revision ID required');
      return request('GET', `/revisions/${id}${buildQuery(args)}`);
    }
  }
};

// Main
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.log('Usage: joplin.js <command> [subcommand] [options]');
    console.log('\nCommands:');
    console.log('  ping                    Check if Joplin service is running');
    console.log('  notes <subcommand>      Manage notes (list, get, create, update, delete, tags, resources)');
    console.log('  folders <subcommand>    Manage notebooks (list, get, create, update, delete, notes)');
    console.log('  tags <subcommand>       Manage tags (list, get, create, update, delete, notes, add-note, remove-note)');
    console.log('  resources <subcommand>  Manage resources (list, get, download, upload, delete, notes)');
    console.log('  search <query>          Search notes');
    console.log('  events <subcommand>     Get events (list, get)');
    console.log('  revisions <subcommand>  Get revisions (list, get)');
    process.exit(0);
  }

  const [cmd, subcmd, ...rest] = args;
  const parsedArgs = parseArgs(subcmd ? [subcmd, ...rest] : rest);
  
  try {
    let result;
    
    if (cmd === 'ping') {
      result = await commands.ping();
    } else if (cmd === 'search') {
      parsedArgs._.unshift(subcmd);
      result = await commands.search(parsedArgs);
    } else if (commands[cmd]) {
      const cmdGroup = commands[cmd];
      if (typeof cmdGroup === 'function') {
        result = await cmdGroup(parsedArgs);
      } else if (cmdGroup[subcmd]) {
        parsedArgs._ = rest.filter(r => !r.startsWith('--'));
        result = await cmdGroup[subcmd](parsedArgs);
      } else {
        console.error(`Unknown subcommand: ${cmd} ${subcmd}`);
        console.error(`Available: ${Object.keys(cmdGroup).join(', ')}`);
        process.exit(1);
      }
    } else {
      console.error(`Unknown command: ${cmd}`);
      process.exit(1);
    }
    
    console.log(JSON.stringify(result, null, 2));
  } catch (e) {
    console.error(JSON.stringify({ error: e.message }, null, 2));
    process.exit(1);
  }
}

main();
