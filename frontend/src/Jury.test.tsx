// @vitest-environment jsdom
import {expect,test} from 'vitest';
import {priority} from './Jury';
test('urgency order follows backend TSP states without recategorizing',()=>{expect(priority('WINDOW_PASSED')).toBeLessThan(priority('DUE_SOON'));expect(priority('DUE_SOON')).toBeLessThan(priority('IN_WINDOW'));});

import {render,screen,cleanup,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {afterEach,vi} from 'vitest';
import {DemoAdmin,RoleSwitcher} from './Jury';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
afterEach(()=>{cleanup();vi.resetAllMocks();});
function mount(node:React.ReactNode){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>{node}</QueryClientProvider>);}
test('admin is absent outside demo mode',async()=>{vi.mocked(api).mockResolvedValue({demo_mode:false});mount(<DemoAdmin token="test">Reset</DemoAdmin>);await waitFor(()=>expect(api).toHaveBeenCalled());expect(screen.queryByText('Admin')).toBeNull();});
test('admin is collapsed in demo mode',async()=>{vi.mocked(api).mockResolvedValue({demo_mode:true});mount(<DemoAdmin token="test">Reset</DemoAdmin>);const admin=await screen.findByText('Admin');expect((admin.parentElement as HTMLDetailsElement).open).toBe(false);});
test('role switch rejects a token for another role',async()=>{vi.mocked(api).mockImplementation(async token=>token==='wrong'?{role:'coordinator'}:{demo_mode:true});const apply=vi.fn();mount(<RoleSwitcher token="test" onToken={apply}/>);fireEvent.click(await screen.findByText('Switch demo role'));fireEvent.change(screen.getByLabelText('Existing role token'),{target:{value:'wrong'}});fireEvent.click(screen.getByRole('button',{name:'Switch role'}));await screen.findByText('Use the existing token for the selected role.');expect(apply).not.toHaveBeenCalled();});
