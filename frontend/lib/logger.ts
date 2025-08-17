// Simple logging utility for frontend
class Logger {
  private logToConsole: boolean = true;
  private logToFile: boolean = false;

  private formatMessage(level: string, message: string, data?: any): string {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      level,
      message,
      data: data || null
    };
    return JSON.stringify(logEntry);
  }

  private log(level: string, message: string, data?: any) {
    const formattedMessage = this.formatMessage(level, message, data);
    
    if (this.logToConsole) {
      console.log(formattedMessage);
    }

    if (this.logToFile) {
      // In a real app, you might send this to a logging service
      // For now, we'll just store in localStorage for debugging
      try {
        const logs = JSON.parse(localStorage.getItem('frontend_logs') || '[]');
        logs.push(JSON.parse(formattedMessage));
        if (logs.length > 100) {
          logs.shift(); // Keep only last 100 logs
        }
        localStorage.setItem('frontend_logs', JSON.stringify(logs));
      } catch (error) {
        console.error('Failed to save log to localStorage:', error);
      }
    }
  }

  info(message: string, data?: any) {
    this.log('INFO', message, data);
  }

  warn(message: string, data?: any) {
    this.log('WARN', message, data);
  }

  error(message: string, data?: any) {
    this.log('ERROR', message, data);
  }

  debug(message: string, data?: any) {
    this.log('DEBUG', message, data);
  }

  // Get logs for debugging
  getLogs(): any[] {
    try {
      return JSON.parse(localStorage.getItem('frontend_logs') || '[]');
    } catch {
      return [];
    }
  }

  // Clear logs
  clearLogs() {
    localStorage.removeItem('frontend_logs');
  }
}

export const logger = new Logger(); 