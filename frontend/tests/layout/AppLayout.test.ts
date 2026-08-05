import AppLayout from '@/layouts/AppLayout.vue';
import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const authMock = {
  user: { id: 'u1', email: 'a@b.com' } as { id: string; email: string } | null,
  logout: vi.fn(),
};

const routerMock = {
  push: vi.fn(),
};

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => authMock,
}));

vi.mock('vue-router', () => ({
  useRouter: () => routerMock,
}));

function mountLayout() {
  return mount(AppLayout, {
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
        RouterView: true,
      },
    },
  });
}

beforeEach(() => {
  authMock.user = { id: 'u1', email: 'a@b.com' };
  authMock.logout = vi.fn();
  routerMock.push = vi.fn();
});

describe('AppLayout', () => {
  it('renders the logged-in user email', () => {
    const wrapper = mountLayout();
    expect(wrapper.text()).toContain('a@b.com');
  });

  it('renders nav links to each section', () => {
    const wrapper = mountLayout();
    const links = wrapper.findAll('nav a');

    expect(links.map((l) => l.text())).toEqual(['Dashboard', 'Upload', 'Gallery', 'Search']);
  });

  it('logs out and redirects to login on logout click', async () => {
    const wrapper = mountLayout();
    const logoutButton = wrapper.findAll('button').find((b) => b.text() === 'Logout')!;
    await logoutButton.trigger('click');

    expect(authMock.logout).toHaveBeenCalledTimes(1);
    expect(routerMock.push).toHaveBeenCalledWith({ name: 'login' });
  });

  it('renders without crashing when there is no user', () => {
    authMock.user = null;
    const wrapper = mountLayout();
    const logoutButton = wrapper.findAll('button').find((b) => b.text() === 'Logout');
    expect(logoutButton?.text()).toBe('Logout');
  });
});
