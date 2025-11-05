/**
 * TypeScript types for test execution events
 */

export enum EventType {
  TEST_START = 'TEST_START',
  TEST_PROGRESS = 'TEST_PROGRESS',
  TEST_LOG = 'TEST_LOG',
  TEST_SUCCESS = 'TEST_SUCCESS',
  TEST_ERROR = 'TEST_ERROR',
  TEST_WARNING = 'TEST_WARNING',
  TEST_COMPLETE = 'TEST_COMPLETE',
  CONNECTION_STATUS = 'CONNECTION_STATUS',
  PING = 'PING',
  ERROR = 'ERROR'
}

export enum LogLevel {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error'
}

export enum ConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  ERROR = 'error'
}

export interface BaseEvent {
  type: EventType;
  test_id: string;
  timestamp: string;
}

export interface TestStartEvent extends BaseEvent {
  type: EventType.TEST_START;
  data: {
    total_steps: number;
    base_url: string;
    scenario_count: number;
  };
}

export interface TestProgressEvent extends BaseEvent {
  type: EventType.TEST_PROGRESS;
  data: {
    step: number;
    total_steps: number;
    step_name: string;
    percentage: number;
  };
}

export interface TestLogEvent extends BaseEvent {
  type: EventType.TEST_LOG;
  data: {
    level: LogLevel;
    message: string;
    [key: string]: any;
  };
}

export interface TestSuccessEvent extends BaseEvent {
  type: EventType.TEST_SUCCESS;
  data: {
    step: number;
    step_name: string;
    duration: number;
    result: any;
  };
}

export interface TestErrorEvent extends BaseEvent {
  type: EventType.TEST_ERROR;
  data: {
    step?: number;
    error: string;
    details?: any;
    fatal?: boolean;
  };
}

export interface TestWarningEvent extends BaseEvent {
  type: EventType.TEST_WARNING;
  data: {
    step?: number;
    warning: string;
    details?: any;
  };
}

export interface TestCompleteEvent extends BaseEvent {
  type: EventType.TEST_COMPLETE;
  data: {
    total_steps: number;
    success_count: number;
    failure_count: number;
    duration: number;
    results: any[];
  };
}

export interface ConnectionStatusEvent {
  type: 'CONNECTION_STATUS';
  status: ConnectionStatus;
  test_id: string;
  subscriber_id?: string;
}

export interface PingEvent {
  type: 'PING';
  timestamp: string | null;
}

export interface ErrorEvent {
  type: 'ERROR';
  error: string;
}

export type TestEvent =
  | TestStartEvent
  | TestProgressEvent
  | TestLogEvent
  | TestSuccessEvent
  | TestErrorEvent
  | TestWarningEvent
  | TestCompleteEvent
  | ConnectionStatusEvent
  | PingEvent
  | ErrorEvent;

export interface TestProgress {
  currentStep: number;
  totalSteps: number;
  stepName: string;
  percentage: number;
  successCount: number;
  failureCount: number;
  warningCount: number;
}

export interface TestStats {
  totalTests: number;
  passed: number;
  failed: number;
  duration: number;
  isComplete: boolean;
}
