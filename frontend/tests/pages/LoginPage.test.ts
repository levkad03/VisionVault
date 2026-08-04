import LoginPage from '@/pages/LoginPage.vue';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';

const authMock = {
  login: vi.fn(),
};

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => authMock,
}));

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: { template: '<div/>' } },
      { path: '/register', name: 'register', component: { template: '<div/>' } },
      { path: '/', name: 'dashboard', component: { template: '<div/>' } },
    ],
  });
}

async function mountPage() {
  const router = createTestRouter();
  router.push('/login');
  await router.isReady();
  const wrapper = mount(LoginPage, { global: { plugins: [router] } });
  return { wrapper, router };
}

beforeEach(() => {
  authMock.login = vi.fn();
});

describe('LoginPage', () => {
  it('renders email, password, and a submit button', async () => {
    const { wrapper } = await mountPage();
    expect(wrapper.find('input#email').exists()).toBe(true);
    expect(wrapper.find('input#password').attributes('type')).toBe('password');
    expect(wrapper.find('button[type="submit"]').text()).toBe('Log in');
  });

  it('logs in with entered credentials and navigates to dashboard', async () => {
    authMock.login.mockResolvedValue(undefined);
    const { wrapper, router } = await mountPage();
    vi.spyOn(router, 'push');

    await wrapper.find('input#email').setValue('a@b.com');
    await wrapper.find('input#password').setValue('pw123456');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(authMock.login).toHaveBeenCalledWith('a@b.com', 'pw123456');
    expect(router.push).toHaveBeenCalledWith({ name: 'dashboard' });
  });

  it('shows an error and does not navigate on failed login', async () => {
    authMock.login.mockRejectedValue(new Error('401'));
    const { wrapper, router } = await mountPage();
    vi.spyOn(router, 'push');

    await wrapper.find('input#email').setValue('a@b.com');
    await wrapper.find('input#password').setValue('wrong');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(wrapper.text()).toContain('Invalid credentials');
    expect(router.push).not.toHaveBeenCalled();
  });

  it('disables the submit button while the request is in flight', async () => {
    let resolveLogin!: () => void;
    authMock.login.mockReturnValue(new Promise<void>((resolve) => (resolveLogin = resolve)));
    const { wrapper } = await mountPage();

    await wrapper.find('input#email').setValue('a@b.com');
    await wrapper.find('input#password').setValue('pw123456');
    await wrapper.find('form').trigger('submit');

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined();

    resolveLogin();
    await flushPromises();

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined();
  });
});
