import RegisterPage from '@/pages/RegisterPage.vue';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';

const authMock = {
  register: vi.fn(),
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
  router.push('/register');
  await router.isReady();
  const wrapper = mount(RegisterPage, { global: { plugins: [router] } });
  return { wrapper, router };
}

beforeEach(() => {
  authMock.register = vi.fn();
});

describe('RegisterPage', () => {
  it('renders email, password, and a submit button', async () => {
    const { wrapper } = await mountPage();
    expect(wrapper.find('input#email').exists()).toBe(true);
    expect(wrapper.find('input#password').attributes('type')).toBe('password');
    expect(wrapper.find('button[type="submit"]').text()).toBe('Register');
  });

  it('registers with entered credentials and navigates to dashboard', async () => {
    authMock.register.mockResolvedValue(undefined);
    const { wrapper, router } = await mountPage();
    vi.spyOn(router, 'push');

    await wrapper.find('input#email').setValue('a@b.com');
    await wrapper.find('input#password').setValue('pw123456');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(authMock.register).toHaveBeenCalledWith('a@b.com', 'pw123456');
    expect(router.push).toHaveBeenCalledWith({ name: 'dashboard' });
  });

  it('shows the error message when registration rejects with an Error', async () => {
    authMock.register.mockRejectedValue(new Error('REGISTER_USER_ALREADY_EXISTS'));
    const { wrapper, router } = await mountPage();
    vi.spyOn(router, 'push');

    await wrapper.find('input#email').setValue('taken@b.com');
    await wrapper.find('input#password').setValue('pw123456');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(wrapper.text()).toContain('REGISTER_USER_ALREADY_EXISTS');
    expect(router.push).not.toHaveBeenCalled();
  });

  it('falls back to a generic message when registration rejects with a non-Error', async () => {
    authMock.register.mockRejectedValue('network down');
    const { wrapper } = await mountPage();

    await wrapper.find('input#email').setValue('a@b.com');
    await wrapper.find('input#password').setValue('pw123456');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(wrapper.text()).toContain('Registration failed');
  });

  it('disables the submit button while the request is in flight', async () => {
    let resolveRegister!: () => void;
    authMock.register.mockReturnValue(new Promise<void>((resolve) => (resolveRegister = resolve)));
    const { wrapper } = await mountPage();

    await wrapper.find('input#email').setValue('a@b.com');
    await wrapper.find('input#password').setValue('pw123456');
    await wrapper.find('form').trigger('submit');

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined();

    resolveRegister();
    await flushPromises();

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined();
  });
});
